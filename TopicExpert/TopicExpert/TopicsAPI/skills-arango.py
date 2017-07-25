import json
import arango
import re

client = arango.ArangoClient(
  protocol='http',
  host='localhost',
  port='8529',
  username='root',
  password='anya',
  enable_logging=True
)

def get_graph():
  # create or get the database
  print(client.databases())
  # get the user
  try:
    client.user('admin')
  except:
    client.create_user('admin', 'password')
    print("Creating user...")


  dbs = client.databases()
  print("Databases: ", dbs)
  if 'skills' not in dbs:
    db = client.create_database('skills', username='admin', password='password')
    client.grant_user_access('admin', 'skills')
  else:
    db = client.database('skills')

  graphs = db.graphs()
  print("Graphs: ", graphs)
  # get the skills graph
  if len(graphs) < 1:
    skills_graph = db.create_graph('skills_graph')
    skills_graph.create_vertex_collection('skills_verts')
  else:
    skills_graph = db.graph('skills_graph')
    skills_graph.vertex_collection('skill_verts')

  print("Graph success", db, skills_graph, skills_graph.edge_collection('related').count(), skills_graph.edge_definitions())

  if len(skills_graph.edge_definitions()) < 2:
    skills_graph.create_edge_definition(
      name='related',
      from_collections=['skills_verts'],
      to_collections=['skills_verts']
    )
    skills_graph.create_edge_definition(
      name='subtopic',
      from_collections=['skills_verts'],
      to_collections=['skills_verts']
    )
  return skills_graph

def import_skills_from_json(graph):
  with open(r'linkedin_topics_7-23-17.json') as file:
    data = json.load(file)
  company = u'Microsoft'
  skill_verts = graph.vertex_collection('skills_verts')
  related = graph.edge_collection('related')
  skills = []
  for skill in data:
    if skill['companies'] is not None:
      if company in skill['companies']:
        name1 = re.sub('[\s&/]', '', skill['name'])
        name = re.sub('#', '', name1)
        print(name, skill['name'], skill['count'], skill['skills'])
        try:
          skill_verts.insert({'_key': name, 'name': skill['name'], 'users': skill['count']})
        except arango.ArangoError as e:
          print(e.message)
          pass
        if skill['skills'] is not None:
          for k, v in skill['skills'].items():
            sk_key1 = re.sub('[\s&/]', '', k)
            sk_key = re.sub('#', '', sk_key1)
            try:
              skill_verts.insert({'_key': sk_key, 'name': k, 'users': v})
            except arango.ArangoError as e:
              print(sk_key, e.message)
              pass
            related.insert({
              '_from': 'skills_verts/%s' % name,
              '_to': 'skills_verts/%s' % sk_key
            })
            print("Skill edge inserted", skill['name'], k)

def main():
  skills_graph = get_graph()
  import_skills_from_json(skills_graph)

if __name__ == '__main__':
  main()

