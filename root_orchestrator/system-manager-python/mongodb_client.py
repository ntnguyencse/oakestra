import os
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime

MONGO_URL = os.environ.get('CLOUD_MONGO_URL')
MONGO_PORT = os.environ.get('CLOUD_MONGO_PORT')

MONGO_ADDR_CLUSTERS = 'mongodb://' + str(MONGO_URL) + ':' + str(MONGO_PORT) + '/clusters'
MONGO_ADDR_JOBS = 'mongodb://' + str(MONGO_URL) + ':' + str(MONGO_PORT) + '/jobs'

mongo_clusters = None
mongo_jobs = None


app = None

CLUSTERS_FRESHNESS_INTERVAL = 45


def mongo_init(flask_app):
    global app
    global mongo_clusters, mongo_jobs

    app = flask_app

    # app.config["MONGO_URI"] = MONGO_ADDR
    mongo_clusters = PyMongo(app, uri=MONGO_ADDR_CLUSTERS)
    mongo_jobs = PyMongo(app, uri=MONGO_ADDR_JOBS)
    app.logger.info("MONGODB - init mongo")


# ......... CLUSTER OPERATIONS ..............
#############################################

def mongo_upsert_cluster(cluster_ip, message):
    global mongo_clusters
    app.logger.info("MONGODB - upserting cluster...")
    clusters = mongo_clusters.db.clusters
    cluster_info = message['cluster_info']
    cluster_name = message['cluster_name']
    cluster_location = message['cluster_location']
    cluster_port = message['port']
    result_obj = clusters.update_one({'cluster_name': cluster_name},
                                     {'$set': {'ip': cluster_ip, 'clusterinfo': cluster_info, 'port': cluster_port,
                                               'cluster_location': cluster_location}},
                                     upsert=True)

    cluster_obj = clusters.find_one({'cluster_name': cluster_name})

    app.logger.info("MONGODB - cluster_id: {0}".format(cluster_obj['_id']))
    return cluster_obj['_id']


def mongo_find_cluster_by_id(cluster_id):
    global mongo_clusters
    return mongo_clusters.db.clusters.find_one(cluster_id)


def mongo_get_all_clusters():
    global mongo_clusters
    return mongo_clusters.db.clusters.find()


def mongo_find_one_cluster():
    """Finds first cluster occurrence"""
    global mongo_clusters
    return mongo_clusters.db.clusters.find_one()


def mongo_find_all_active_clusters():
    global mongo_clusters
    app.logger.info('Finding the active cluster orchestrators...')
    now_timestamp = datetime.now().timestamp()
    return mongo_clusters.db.clusters.find(
        {'last_modified_timestamp': {'$gt': now_timestamp - CLUSTERS_FRESHNESS_INTERVAL}})


def mongo_find_cluster_by_id_and_incr_node(c_id):
    global mongo_clusters
    return mongo_clusters.db.clusters.update_one({'_id': c_id}, {'$inc': {'nodes': 1}}, upsert=True)


def mongo_find_cluster_by_id_and_set_number_of_nodes(c_id, number_of_nodes):
    global mongo_clusters
    return mongo_clusters.db.clusters.update_one({'_id': c_id}, {'$inc': {'nodes': number_of_nodes}}, upsert=True)


def mongo_find_cluster_by_id_and_decr_node(c_id):
    global mongo_clusters
    return mongo_clusters.db.clusters.update_one({'_id': c_id}, {'$inc': {'nodes': -1}}, upsert=True)


def mongo_find_cluster_by_location(location):
    global mongo_clusters
    try:
        return mongo_clusters.db.clusters.find_one({'cluster_location': location})
    except Exception as e:
        return "Error"


def mongo_update_cluster_information(cluster_id, data):
    """Save aggregated Cluster Information"""
    global mongo_clusters

    cpu_percent = data.get('cpu_percent')
    cpu_cores = data.get('cpu_cores')
    memory_percent = data.get('memory_percent')
    memory_in_mb = data.get('cumulative_memory_in_mb')
    nodes = data.get('number_of_nodes')
    technology = data.get('technology')
    more = data.get('more')

    jobs = data.get('jobs')
    for j in jobs:
        print(j)
        mongo_update_job_status(job_id=j.get('system_job_id'), status=j.get('status'))

    datetime_now = datetime.now()
    datetime_now_timestamp = datetime.timestamp(datetime_now)

    mongo_clusters.db.clusters.\
        find_one_and_update({'_id': ObjectId(cluster_id)},
                            {'$set': {'aggregated_cpu_percent': cpu_percent, 'total_cpu_cores': cpu_cores,
                                      'aggregated_memory_percent': memory_percent, 'memory_in_mb': memory_in_mb,
                                      'active_nodes': nodes, 'technology': technology, 'more': more,
                                      'last_modified': datetime_now, 'last_modified_timestamp': datetime_now_timestamp}},
                            upsert=True)


# ......... JOB OPERATIONS .........................
####################################################

def mongo_insert_job(obj):
    global mongo_jobs
    app.logger.info("MONGODB - insert job...")

    job_description = obj.get('file_content')
    job_name = job_description.get('job_name')

    jobs = mongo_jobs.db.jobs
    new_job = jobs.find_one_and_update({'job_name': job_name},
                                       {'$set': {'job_name': job_name, 'file_content': job_description}},
                                       upsert=True, return_document=True)
    app.logger.info("MONGODB - job {} inserted".format(str(new_job.get('_id'))))
    return str(new_job.get('_id'))


def mongo_get_all_jobs():
    global mongo_jobs
    return mongo_jobs.db.jobs.find()


def mongo_get_job_status(job_id):
    global mongo_jobs
    return mongo_jobs.db.jobs.find_one({'_id': ObjectId(job_id)}, {'status': 1})['status'] + '\n'


def mongo_update_job_status(job_id, status):
    global mongo_jobs
    return mongo_jobs.db.jobs.update_one({'_id': ObjectId(job_id)}, {'$set': {'status': status}})


def mongo_find_job_by_id(job_id):
    global mongo_jobs
    return mongo_jobs.db.jobs.find_one(ObjectId(job_id))


# .......... BOTH CLUSTER and JOB OPERATIONS .........
######################################################

def mongo_find_cluster_of_job(job_id):
    app.logger.info('Find job by Id and return cluster...')
    job_obj = mongo_jobs.db.jobs.find_one({'_id': ObjectId(job_id)}, {'cluster': 1})  # return just the assgined cluster of the job
    cluster_id = job_obj.get('cluster')
    return mongo_find_cluster_by_id(cluster_id)