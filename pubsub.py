# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

from awscrt import mqtt, http
from awsiot import mqtt_connection_builder
import sys
import threading
import time
import json
from utils.command_line_utils import CommandLineUtils
import random
import signal

# This sample uses the Message Broker for AWS IoT to send and receive messages
# through an MQTT connection. On startup, the device connects to the server,
# subscribes to a topic, and begins publishing messages to that topic.
# The device should receive those same messages back from the message broker,
# since it is subscribed to that same topic.

# cmdData is the arguments/input from the command line placed into a single struct for
# use in this sample. This handles all of the command line parsing, validating, etc.
# See the Utils/CommandLineUtils for more information.
cmdData = CommandLineUtils.parse_sample_input_pubsub()

received_count = 0
publish_count = 0
published_results = []
received_all_event = threading.Event()

received_start_time = 0
received_end_time = 0
received_msgs_per_second = 0


# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print("Resubscribe results: {}".format(resubscribe_results))

    for topic, qos in resubscribe_results['topics']:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))


# define the Ctrl_C handler
def handler(signum, frame):
    print("\nInterrupted: publish_count = " + str(message_count) +
          ", received_count = " + str(received_count))
    print("published_results[] contains " + str(len(published_results)))

    success = []
    failures = []
    for r in published_results:
        try:
            print(str(r[1]) + " Finished=" + str(r[0].done()) + ", Running=" + str(r[0].running()) + ", Result=" + str(
                 r[0].result()))
            success.append(r)
        except Exception as e:
            print(str(r[1]) + " Finished=" + str(r[0].done()) + ", Running=" + str(r[0].running()) + ", " + str(e))
            failures.append(r)
    print(str(len(success)) + " successful. " +
          str(len(failures)) + " failures.")
    exit(0)


signal.signal(signal.SIGINT, handler)


# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    # print("<-- Received message from topic '{}': {}".format(topic, payload))
    print_stats()
    global received_count
    global received_start_time
    global received_end_time
    if received_count == 0:
        received_start_time = time.time()

    received_count += 1
    if received_count == cmdData.input_count:
        received_end_time = time.time()
        received_all_event.set()


def print_stats():
    print("Published = " + str(publish_count) + ", Received = " + str(received_count) +
          ", Publish msgs/sec = " + str(publish_count / (end_time - start_time)), end="\r")


if __name__ == '__main__':
    # Create the proxy options if the data is present in cmdData
    proxy_options = None
    if cmdData.input_proxy_host is not None and cmdData.input_proxy_port != 0:
        proxy_options = http.HttpProxyOptions(
            host_name=cmdData.input_proxy_host,
            port=cmdData.input_proxy_port)

    # Create a MQTT connection from the command line data
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=cmdData.input_endpoint,
        port=cmdData.input_port,
        cert_filepath=cmdData.input_cert,
        pri_key_filepath=cmdData.input_key,
        ca_filepath=cmdData.input_ca,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        client_id=cmdData.input_clientId,
        clean_session=False,
        keep_alive_secs=30,
        http_proxy_options=proxy_options)

    start_time = time.time()
    end_time = 0

    if not cmdData.input_is_ci:
        print(f"Connecting to {cmdData.input_endpoint} with client ID '{cmdData.input_clientId}'...")
    else:
        print("Connecting to endpoint with client ID")
    connect_future = mqtt_connection.connect()

    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")

    message_count = cmdData.input_count
    message_topic = cmdData.input_topic
    message_string = cmdData.input_message

    # Subscribe
    print("Subscribing to topic '{}'...".format(message_topic))
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=message_topic,
        qos=mqtt.QoS.AT_MOST_ONCE,
        callback=on_message_received)

    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))

    # Publish message to server desired number of times.
    # This step is skipped if message is blank.
    # This step loops forever if count was set to 0.
    if message_string:
        if message_count == 0:
            print("Sending messages until program killed")
        else:
            print("Sending {} message(s)".format(message_count))
            print(time.time())
            print("\n")
        publish_count = 1
        while (publish_count <= message_count) or (message_count == 0):
            # message = "{} [{}]".format(message_string, publish_count)
            message = '{"msg": "Hello World!","ts": ' + \
                      str(time.time()) + ',"value": ' + str(random.randint(0, 10)
                                                            ) + ',"seq": ' + str(publish_count) + '}'
            print_stats()
            message_json = json.dumps(message)

            published_results.append(mqtt_connection.publish(
                topic=message_topic,
                payload=message_json,
                qos=mqtt.QoS.AT_LEAST_ONCE))

            publish_count += 1

        end_time = time.time()
        print(end_time)
        publish_count -= 1

    # Wait for all messages to be received.
    # This waits forever if count was set to 0.
    if message_count != 0 and not received_all_event.is_set():
        print("Waiting for all messages to be received...")

    received_all_event.wait()
    print("{} message(s) received.".format(received_count))

    # Disconnect
    print("Disconnecting...")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")

    time.sleep(1)
    print("Published = " +
          str(publish_count) +
          ", Received = " +
          str(received_count) +
          ", Publish msgs/sec = " +
          str(publish_count /
              (end_time -
               start_time)) +
          ", Received msg/sec = " +
          str(received_count /
              (received_end_time -
               received_start_time)))
