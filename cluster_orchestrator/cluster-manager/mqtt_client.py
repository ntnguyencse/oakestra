import os
import re
import json
from datetime import datetime

from flask_mqtt import Mqtt
from mongodb_client import mongo_find_node_by_id_and_update_cpu_mem


mqtt = None
app = None


def mqtt_init(flask_app):
    global mqtt
    global app
    app = flask_app
    
    app.config['MQTT_BROKER_URL'] = os.environ.get('MQTT_BROKER_URL') 
    app.config['MQTT_BROKER_PORT'] = int(os.environ.get('MQTT_BROKER_PORT'))
    app.config['MQTT_REFRESH_TIME'] = 1.0  # refresh time in seconds
    mqtt = Mqtt(app)

    @mqtt.on_connect()
    def handle_connect(client, userdata, flags, rc):
        app.logger.info("MQTT - Connected to MQTT Broker")
        mqtt.subscribe('nodes/+/information')

    @mqtt.on_log()
    def handle_logging(client, userdata, level, buf):
        if level == 'MQTT_LOG_ERR':
            app.logger.info('Error: {}'.format(buf))

    @mqtt.on_message()
    def handle_mqtt_message(client, userdata, message):
        data = dict(
            topic=message.topic,
            payload=message.payload.decode()
        )
        app.logger.info('MQTT - Received from worker: ')
        app.logger.info(data)

        topic = data['topic']
        # if topic starts with nodes and ends with information
        re_nodes_information_topic = re.search("^nodes/.*/information$", topic)
        if re_nodes_information_topic is not None:
            # print(topic)
            topic_split = topic.split('/')
            client_id = topic_split[1]
            payload = json.loads(data['payload'])
            # print(payload)
            cpu_used = payload.get('cpu')
            mem_used = payload.get('memory')
            cpu_cores_free = payload.get('free_cores')
            memory_free_in_MB = payload.get('memory_free_in_MB')
            mongo_find_node_by_id_and_update_cpu_mem(client_id, cpu_used, cpu_cores_free, mem_used, memory_free_in_MB)


def mqtt_publish_edge_deploy(worker_id, job):
    topic = 'nodes/' + worker_id + '/control/deploy'
    data = job
    job_id = str(job.get('_id'))  # serialize ObjectId to string
    job.__setitem__('_id', job_id)
    mqtt.publish(topic, json.dumps(data))  # MQTT cannot send JSON, dump it to String here


def mqtt_publish_edge_delete(worker_id, job):
    topic = 'nodes/' + worker_id + '/control/delete'
    data = job
    job_id = str(job.get('_id'))
    job.__setitem__('_id', job_id)
    mqtt.publish(topic, json.dumps(data))