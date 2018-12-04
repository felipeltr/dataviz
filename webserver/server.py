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

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



DB_USER = "aabf"
DB_PASSWORD = "sunburstviz"

DB_SERVER = "localhost"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/gradcafe"


engine = create_engine(DATABASEURI)



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
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



if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=80, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    threaded=True

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
