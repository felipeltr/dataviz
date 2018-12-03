#!/usr/bin/env python2.7


import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response
import flask

import pandas as pd

from nesting import Nest

from collections import OrderedDict

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



DB_USER = "aabf"
DB_PASSWORD = "sunburstviz"

DB_SERVER = "localhost"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/gradcafe"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
# engine.execute("""DROP TABLE IF EXISTS test;""")
# engine.execute("""CREATE TABLE IF NOT EXISTS test (
#   id serial,
#   name text
# );""")
# engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



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

filters = [
  ('program','Program'),
  ('degree','Degree'),
  ('institution', 'Institution'),
  ('term', 'Term'),

]



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
  
  return render_template("index.html",options=options)



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


@app.route('/nested', methods=['POST'])
def nested():

  attrs = ['institution', 'degree', 'term', 'decision']
  attrs = ['institution', 'degree', 'decision']

  attrs = request.form.getlist('burstCols[]')

  attrStr = ', '.join(attrs)

  query = """
    SELECT {attrs}, count(*) as total
    FROM results
    where institution IN ('Columbia University', 'Carnegie Mellon University (CMU)')
    and term in ('F18', 'F17')
    group by {attrs}
  """.format(
    attrs=attrStr
  )

  results = pd.read_sql(query, g.conn).to_dict(orient='records')

  nest = Nest()
  for a in attrs:
    nest = nest.key(a)

  nested = _entries(nest,nest.map(results))

  # return str(nested)

  return flask.jsonify(dict(name='sunburst',children=nested))




  # return flask.jsonify(pd.read_sql(query, g.conn).to_json(orient='records'))




#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the functio name is another() rather than index()
# the functions for each app.route needs to have different names
#
# @app.route('/another')
# def another():
#   return render_template("anotherfile.html")


# # Example of adding new data to the database
# @app.route('/add', methods=['POST'])
# def add():
#   name = request.form['name']
#   print name
#   cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)';
#   g.conn.execute(text(cmd), name1 = name, name2 = name);
#   return redirect('/')


# @app.route('/login')
# def login():
#     abort(401)
#     this_is_never_executed()


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
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
