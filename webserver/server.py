#!/usr/bin/env python2.7


import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response
import flask

import numpy as np
import pandas as pd

from nesting import Nest

from collections import OrderedDict

import io
import random
from flask import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from wordcloud import WordCloud

import base64

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



DB_USER = "aabf"
DB_PASSWORD = "sunburstviz"

DB_SERVER = "localhost"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/gradcafe"


engine = create_engine(DATABASEURI)



@app.before_request
def before_request():
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  try:
    g.conn.close()
  except Exception as e:
    pass


@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


# Configs

filters = [
  ('program','Program'),
  ('degree','Degree'),
  ('institution', 'Institution'),
  ('term', 'Term'),
  ('status', 'Status')
]

scoreBuckets = OrderedDict([
  ('q',{'colname':'q', 'title':'Q-GRE', 'range':(130,171,5) }),
  ('v',{'colname':'v', 'title':'V-GRE', 'range':(130,171,5) }),
  ('w',{'colname':'w', 'title':'W-GRE', 'range':(1,7.1,0.5) }),
  ('gpa',{'colname':'gpa', 'title':'UG-GPA', 'range':(2.5,4.01,0.25) })
])
  


#############

@app.route('/')
def index():

  options = []

  for colname, title in filters:
    cursor = g.conn.execute("""
        select distinct {colname}
        from results
        where {colname} is not null
        order by 1
      """.format(
        colname=colname
      ))

    values = cursor.fetchall()

    options.append({
        'colname': colname,
        'title': title,
        'values': list(map(lambda x: x[0], values))
      })

  # return flask.jsonify(options)
  
  return render_template("index.html",
    options=options,
    scores=scoreBuckets.values()
  )



def _entries(self, data, depth=0):
  if depth == (len(self._keys) - 1):
      return [ OrderedDict([('name',k), ('size',v[0]['total'])]) for k, v in data.iteritems() ]
      # return data
  
  values = [ OrderedDict([('name',k), ('children',_entries(self, v, depth+1))]) for k, v in data.iteritems() ]
  
  # keySort = self._sortKeys[depth]
  # if keySort:
  #     propCmp = keySort.pop('cmp', cmp)
  #     values = sorted(values, cmp=lambda a, b: propCmp(a['key'], b['key']), **keySort)
  
  return values

def parseFilters(filters):

  nested = Nest().key('name').map(filters)

  conditions = []

  for name, items in nested.items():
    values = ', '.join(map(lambda x: "'"+x['value']+"'",items))

    conditions.append(name+' IN ( '+values+')')

  condition = " AND ".join(conditions)

  return condition


@app.route('/nested', methods=['POST'])
def nested():

  # attrs = ['institution', 'degree', 'term', 'decision']
  # attrs = ['institution', 'degree', 'decision']

  # attrs = request.form.getlist('burstCols[]')

  data = request.get_json()

  attrs = data['burstCols']

  filterCondition = parseFilters(data['filters'])

  # print data

  attrStr = ', '.join(attrs)

  query = """
    SELECT {attrs}, count(*) as total
    FROM results
    --where
    --institution IN ('Columbia University', 'Carnegie Mellon University (CMU)') and
    --term in ('F18', 'F17')
    {extraCondition}
    group by {attrs}
  """.format(
    attrs=attrStr,
    extraCondition='where '+filterCondition if filterCondition != '' else ''
  )

  results = pd.read_sql(query, g.conn).to_dict(orient='records')

  nest = Nest()
  for a in attrs:
    nest = nest.key(a)

  nested = _entries(nest,nest.map(results))


  return flask.jsonify(dict(name='sunburst',children=nested))




@app.route('/scores', methods=['POST'])
def scores():

  data = request.get_json()

  score = data['score']
  selection = data['selection']
  attrs = data['burstCols']
  filterCondition = parseFilters(data['filters'])


  # score = 'v'
  # selection = 'sunburst/Columbia University/MS'
  # attrs = ['institution', 'degree', 'decision']
  # filterCondition = ''

  selectionValues = selection.split('/')[1:]
  selectionAttrs = attrs[:len(selectionValues)]

  groupingCol = attrs[len(selectionValues)] if len(attrs) > len(selectionValues) else "'-'"

  binRange = np.arange(*scoreBuckets[score]['range'])
  bins = list(zip(binRange[:-1],binRange[1:]))

  selectionCond = parseFilters([{'name':n,'value':v} for n,v in zip(selectionAttrs,selectionValues) ])


  colTemplate = ' SUM(CASE WHEN {col} > {min} AND {col} <= {max} THEN 1 ELSE 0 END) AS "( {min}; {max} ]" '

  cols = [colTemplate.format(col=score,min=v0,max=v1) for v0, v1 in bins]

  query = """
    select
      {groupingCol} as group,
      {cols}
    from results
    where true
    {selCond}
    {filterCond}
    group by 1
    order by 1
  """.format(
    groupingCol=groupingCol,
    cols=',\n'.join(cols),
    selCond='and '+selectionCond if selectionCond != '' else '',
    filterCond='and '+filterCondition if filterCondition != '' else '',
  )

  csv = pd.read_sql(query,g.conn).set_index('group').T.to_csv(index=True,index_label='group')

  cursor = g.conn.execute("""
      insert into dump(content) values ('{csv}') returning id
    """.format(
      csv=csv
    ))

  values = cursor.fetchone()

  return flask.jsonify({'id':values[0]})



#########################################################


@app.route('/timeline', methods=['POST'])
def timeline():

  data = request.get_json()

  dateagg = data['dateagg']
  selection = data['selection']
  attrs = data['burstCols']
  filterCondition = parseFilters(data['filters'])

  # selection = 'sunburst/Columbia University/Master'
  # attrs = ['institution', 'degree', 'decision']
  # filterCondition = ''

  selectionValues = selection.split('/')[1:]
  selectionAttrs = attrs[:len(selectionValues)]

  groupingCol = attrs[len(selectionValues)] if len(attrs) > len(selectionValues) else "'-'"

  selectionCond = parseFilters([{'name':n,'value':v} for n,v in zip(selectionAttrs,selectionValues) ])

  monthExpr = "substring(date::text from 1 for 7)" if dateagg == 'my' else 'substring(date::text from 6 for 2)'

  query = """
    with grouped as (
      select  date_trunc('month', date::timestamp) date, {groupingCol} as "group", count(*) as ct
      from results
      where date is not null
      {selCond}
      {filterCond}
      group by 1, 2
    ), series as (
      select *
      from grouped
      UNION ALL
      select generate_series((select min(date) from grouped),(select max(date) from grouped ),'1 month'), 'dummy', 0
    )
    select {monthExpr} as month, "group", sum(ct) as ct
    from series
    group by 1, 2
    order by 1, 2

  """.format(
    monthExpr=monthExpr,
    groupingCol=groupingCol,
    selCond='and '+selectionCond if selectionCond != '' else '',
    filterCond='and '+filterCondition if filterCondition != '' else '',
  )

  df = pd.read_sql(query,g.conn)

  pivoted = df.pivot_table(
    values='ct',
    index='month',
    columns='group',
    aggfunc=np.sum,
    dropna=False,
    fill_value=0
  ).drop('dummy',axis=1)

  csv = pivoted.to_csv(index=True,index_label='group')

  cursor = g.conn.execute("""
      insert into dump(content) values ('{csv}') returning id
    """.format(
      csv=csv
    ))

  values = cursor.fetchone()

  return flask.jsonify({'id':values[0]})








@app.route('/getdump/<did>')
def getdump(did):
  cursor = g.conn.execute("""
      select content
      from dump
      where id = {did}
    """.format(
      did=did
    ))

  content = cursor.fetchone()[0]

  return content




@app.route('/wordcloud', methods=['POST'])
def plot_png():

  data = request.get_json()

  selection = data['selection']
  attrs = data['burstCols']
  filterCondition = parseFilters(data['filters'])

  # selection = 'sunburst/Columbia University/Master'
  # attrs = ['institution', 'degree', 'decision']
  # filterCondition = ''

  selectionValues = selection.split('/')[1:]
  selectionAttrs = attrs[:len(selectionValues)]

  selectionCond = parseFilters([{'name':n,'value':v} for n,v in zip(selectionAttrs,selectionValues) ])

  query = """
    with top as (
      SELECT unnest(word_arr) AS word, count(*) AS ct
      FROM   results
      where true
      {selCond}
      {filterCond}
      GROUP  BY 1
      ORDER  BY 2 DESC
    )
    select *
    from top
    where word not in (
      select *
      from stopwords
    ) and length(word)>1
    LIMIT 60
  """.format(
    selCond='and '+selectionCond if selectionCond != '' else '',
    filterCond='and '+filterCondition if filterCondition != '' else '',
  )


  cursor = g.conn.execute(query)

  values = cursor.fetchall()

  freqs = {t[0]: t[1] for t in values} if len(values) > 0 else {' ': 0}

  fig = create_figure(freqs)
  output = io.BytesIO()
  FigureCanvas(fig).print_png(output)
  return 'data:image/png;base64,'+base64.b64encode(output.getvalue())
  return Response(output.getvalue(), mimetype='image/png')

def create_figure(freqs):
    fig = Figure(figsize=(4.8,3.6), dpi=150)
    # f = {'test':10,'abc':5,'def':7,'viz':2}
    freqs = {' ':1}
    wordcloud = WordCloud(background_color='white').generate_from_frequencies(freqs)
    # plt.figure()
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt = fig.add_subplot(1, 1, 1)
    plt.imshow(wordcloud, interpolation="bilinear")

    plt.axis("off")
    return fig



if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=80, type=int)
  def run(debug, threaded, host, port):

    threaded=True

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
