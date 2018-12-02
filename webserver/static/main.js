
// alert('aaa')

data = $.ajax({
  dataType: "json",
  url: '/nested',
  async: false
}).responseJSON

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


width = 200

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


var root;
var svg;
var g;

function sundraw() {  


  root = partition(data);

  svg = d3.select("#sunburst")

  console.log(svg)
  
  g = svg.append("g");
  
  g.append("g")
      .attr("fill-opacity", 0.6)
    .selectAll("path")
    .data(root.descendants().filter(d => d.depth))
    .enter().append("path")
      .attr("fill", d => { while (d.depth > 1) d = d.parent; return color(d.data.name); })
      .attr("d", arc)
    .append("title")
      .text(d => `${d.ancestors().map(d => d.data.name).reverse().join("/")}\n${format(d.value)}`);

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
      .style('font', '4px sans-serif')
      .text(d => d.data.name);

  // document.body.appendChild(svg.node());

  var box = g.node().getBBox();

  svg
      .attr("width", box.width)
      .attr("height", box.height)
      .attr("viewBox", `${box.x} ${box.y} ${box.width} ${box.height}`);

  return svg.node();

}  



sundraw()
