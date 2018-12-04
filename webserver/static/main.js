
// alert('aaa')

// data = {
// 	name: 'flare',
// 	children: [
// 		{
// 			name: 'flare',
// 			children: [
// 				{name: 'flare2', size:12},
// 				{name: 'flare3', size:5},
// 			]
// 		},
// 		{
// 			name: 'flare4',
// 			children: [
// 				{name: 'flare5', size:12},
// 				{name: 'flare6', size:5},
// 			]
// 		},
	
// 	]

// }

function bardraw(selector, title, dumpId) {

  var svg = d3.select(selector)

  svg.selectAll('*').remove()

  var margin = {top: 20, right: 20, bottom: 30, left: 40},
      width = +svg.attr("width") - margin.left - margin.right,
      height = +svg.attr("height") - margin.top - margin.bottom,
      g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  var x0 = d3.scaleBand()
      .rangeRound([0, width])
      .paddingInner(0.1);

  var x1 = d3.scaleBand()
      .padding(0.05);

  var y = d3.scaleLinear()
      .rangeRound([height, 0]);

  var z = d3.scaleOrdinal()
      .range(["#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"]);

  d3.csv("getdump/"+dumpId, function(d, i, columns) {
    for (var i = 1, n = columns.length; i < n; ++i) d[columns[i]] = +d[columns[i]];
    return d;
  }).then( function( data) {

    // console.log(error);
    // console.log(data);
    // d=data
    // if (error) throw error;

    var keys = data.columns.slice(1);

    x0.domain(data.map(function(d) { return d.group; }));
    x1.domain(keys).rangeRound([0, x0.bandwidth()]);
    y.domain([0, d3.max(data, function(d) { return d3.max(keys, function(key) { return d[key]; }); })]).nice();
    // y.domain([0, 15000000]).nice();

    g.append("g")
      .selectAll("g")
      .data(data)
      .enter().append("g")
        .attr("transform", function(d) { return "translate(" + x0(d.group) + ",0)"; })
      .selectAll("rect")
      .data(function(d) { return keys.map(function(key) { return {key: key, value: d[key]}; }); })
      .enter().append("rect")
        .attr("x", function(d) { return x1(d.key); })
        .attr("y", function(d) { return y(d.value); })
        .attr("width", x1.bandwidth())
        .attr("height", function(d) { return height - y(d.value); })
        .attr("fill", function(d) { return z(d.key); });

    g.append("g")
        .attr("class", "axis")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x0));

    g.append("g")
        .attr("class", "axis")
        .call(d3.axisLeft(y).ticks(null, "s"))
      .append("text")
        .attr("x", 2)
        .attr("y", y(y.ticks().pop()) + 0.5)
        .attr("dy", "0.32em")
        .attr("fill", "#000")
        .attr("font-weight", "bold")
        .attr("text-anchor", "start")
        .text(title);

    var legend = g.append("g")
        .attr("font-family", "sans-serif")
        .attr("font-size", 10)
        .attr("text-anchor", "end")
      .selectAll("g")
      .data(keys.slice().reverse())
      .enter().append("g")
        .attr("transform", function(d, i) { return "translate(0," + i * 20 + ")"; });

    legend.append("rect")
        .attr("x", width - 19)
        .attr("width", 19)
        .attr("height", 19)
        .attr("fill", z);

    legend.append("text")
        .attr("x", width - 24)
        .attr("y", 9.5)
        .attr("dy", "0.32em")
        .text(function(d) { return d; });
  });

}


function redrawScoreBar() {
  dumpId = $.ajax({
    dataType: "json",
    url: '/scores',
    async: false,
    method: 'POST',
    data: JSON.stringify({
      burstCols: burstCols,
      filters: filters,
      score: score,
      selection: selection
    }),
    contentType: "application/json",
  }).responseJSON.id

  bardraw("#scorebar","Score Histogram",dumpId)
}


function updateWordCloud () {

  $.ajax({
    dataType: "json",
    url: '/wordcloud',
    // async: false,
    method: 'POST',
    data: JSON.stringify({
      burstCols: burstCols,
      filters: filters,
      score: score,
      selection: selection
    }),
    contentType: "application/json",
    complete: function (xhr, status) {

      // console.log(xhr)
      data = xhr.responseText

      $('#wordcloud').attr('src',data)

      $('#wordcloud').show('fade',{},400)
    }
  })


}

function hideDrilldown() {
  $('#nodrilldown').show()
  $('#drilldown').hide()

  $('#wordcloud').hide()
}

function showDrilldown() {
  $('#wordcloud').hide()
  redrawScoreBar()
  

  $('#nodrilldown').hide()
  $('#drilldown').show()

  updateWordCloud()
}


// var data;

function sundraw() {  

  var root;
  var svg;
  var g;

  var data = $.ajax({
    dataType: "json",
    url: '/nested',
    async: false,
    method: 'POST',
    data: JSON.stringify({
      burstCols: burstCols,
      filters: filters
    }),
    contentType: "application/json",
  }).responseJSON

  width = 400

  radius = width / 2

  format = d3.format(",d")

  color = d3.scaleOrdinal().range(d3.quantize(d3.interpolateRainbow, data.children.length + 1))

  arc = d3.arc()
    .startAngle(d => d.x0)
    .endAngle(d => d.x1)
    .padAngle(d => Math.min((d.x1 - d.x0) / 2, 0.005))
    .padRadius(radius / 2)
    .innerRadius(d => d.y0)
    .outerRadius(d => d.y1 - 1)

  partition = data => d3.partition()
      .size([2 * Math.PI, radius])
    (d3.hierarchy(data)
      .sum(d => d.size)
      .sort((a, b) => b.value - a.value))


  root = partition(data);

  svg = d3.select("#sunburst")

  svg.selectAll('*').remove()

  console.log(svg)
  
  g = svg.append("g");
  
  paths = g.append("g")
      .attr("fill-opacity", 0.6)
    .selectAll("path")
    .data(root.descendants().filter(d => d.depth))
    .enter().append("path")
      .attr("fill", d => { while (d.depth > 1) d = d.parent; return color(d.data.name); })
      .attr("d", arc)
      .style('cursor', 'pointer');

  paths.append("title")
      .text(d => `${d.ancestors().map(d => d.data.name).reverse().join("/")}\n${format(d.value)}`);


  paths.on("click", function() {

    newselection = $(this).text().split("\n")[0]

    if (newselection == selection) {

      selection = ''

      hideDrilldown()

      paths.attr("fill-opacity", 0.6)

    } else {

      selection = newselection
    
      showDrilldown()

      paths.attr("fill-opacity", 0.2)
      $(this).attr("fill-opacity", 0.7)
    }

  });

  g.append("g")
      .attr("pointer-events", "none")
      .attr("text-anchor", "middle")
    .selectAll("text")
    .data(root.descendants().filter(d => d.depth && (d.y0 + d.y1) / 2 * (d.x1 - d.x0) > 10))
    .enter().append("text")
      .attr("transform", function(d) {
        const x = (d.x0 + d.x1) / 2 * 180 / Math.PI;
        const y = (d.y0 + d.y1) / 2;
        return `rotate(${x - 90}) translate(${y},0) rotate(${x < 180 ? 0 : 180})`;
      })
      .attr("dy", "0.035em")
      .style('font', '8px sans-serif')
      .text(function(d) {
        // console.log(d);

        name = d.data.name;
        if (!name.includes(' '))
          return name

        var matches = name.match(/\((.*?)\)/);

        if (matches) {
            var submatch = matches[1];
            return submatch
        }

        return name.split("University")[0]

      });

      // .text(d => d.data.name);

  // document.body.appendChild(svg.node());

  var box = g.node().getBBox();

  svg
      .attr("width", box.width)
      .attr("height", box.height)
      .attr("viewBox", `${box.x} ${box.y} ${box.width} ${box.height}`);

  return svg.node();

}  




