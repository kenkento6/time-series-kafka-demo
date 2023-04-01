#!/usr/bin/env python
# conda activate bd4hproject
# python bin/processStream.py my-stream
# to do: need to preprocess the data
"""Consumes stream for printing all messages to the console.
"""
import os
import argparse
import json
import sys
import time
import socket
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer

from pyspark.sql import SparkSession
from pyspark.pandas.frame import DataFrame
import numpy as np
import pandas as pd
from pyspark.sql.functions import explode, split, from_json, to_json, col, struct
from pyspark.sql.types import StringType, StructType

from pyspark.sql.functions import col, lower
from pyspark.sql.types import StructField, StructType, StringType
from pyspark.sql.streaming import DataStreamWriter, StreamingQuery

# Define the function to preprocess and send the data to Kafka
def preprocess_and_send_to_kafka(batch_df, batch_id):
    producer_conf = {
    'kafka.bootstrap.servers': '172.18.0.4:29092',
        'client.id': socket.gethostname(),
        'acks':'all', # continuously prints ack every time a message is sent. but slows process down. 
        'retries':5
}
    print('preprocess_and_send_to_kafka called/')
    # Preprocess the data
    preprocessed_df = batch_df #.select(lower(col("value")).alias("value_lower"))
    preprocessed_df.printSchema() 
    print(producer_conf) 
    # Send the preprocessed data to Kafka
    # Todo: Change topic hardcoding 
    preprocessed_df.write.format("kafka")\
        .options(**producer_conf)\
        .option("topic", "call-stream")\
        .option("value.serializer", "org.apache.kafka.common.serialization.StringSerializer")\
        .option("key.serializer", "org.apache.kafka.common.serialization.StringSerializer")\
        .save()
    
print("new version!")
# https://stackoverflow.com/questions/72812187/pythonfailed-to-find-data-source-kafkav
spark = SparkSession.builder.appName('Read CSV File into DataFrame').config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2").getOrCreate()
sc = spark.sparkContext

def msg_process(server, topic):
    # Print the current time and the message.
    # time_start = time.strftime("%Y-%m-%d %H:%M:%S")
    # val = msg.value()
    # dval = json.loads(val)
    # print(time_start, dval)
    # Using this tutorial https://medium.com/@aman.parmar17/handling-real-time-kafka-data-streams-using-pyspark-8b6616a3a084
    sampleDataframe = (
            spark.
            readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", server)
            .option("subscribe", topic)
            .option("startingOffsets", "latest")
            .load()
        )
    
    # Version 1: Just printing the value
    base_df = sampleDataframe.selectExpr("CAST(value as STRING)", "timestamp")
    
    # base_df.writeStream.outputMode("append").format("console").start().awaitTermination()

    # query = base_df.writeStream.outputMode("append").format("console").trigger(processingTime='10 seconds').start()

    # Write the preprocessed DataFrame to Kafka
    kafka_writer: DataStreamWriter = base_df.writeStream.foreachBatch(preprocess_and_send_to_kafka)
    kafka_query: StreamingQuery = kafka_writer.start()

    kafka_query.awaitTermination()

    # Write preprocessing scripts

    # To do: I should start-up another docker that receives the request and runs the prediction.
    # Send request to API

    # Receive result from API

    # Package result into a new Kafka message 

    # Send it back to Kafka

    # VERSION 2: Some additional processing that that cannot be done.

    # sample_schema = (
    #     StructType()
    #     .add("col_a", StringType())
    # )
    # info_dataframe = base_df.select(
    #         from_json(col("value"), sample_schema).alias("sample"), "timestamp"
    #     )
    # info_df_fin = info_dataframe.select("sample.*", "timestamp")

    # query_1.writeStream.outputMode("append").format("console").start().awaitTermination(

    # # print last 5 rows of base_df
    # base_df.show(5, False)

    # spark.streams.awaitAnyTermination()
    # end version 1 


    # Version 3: writing back to kafka
    # query_1 = info_df_fin
    # 
    # result_1 = (
    #     query_1.selectExpr(
    #         "CAST(col_a AS STRING)"
    #     )
    #     .withColumn("value", to_json(struct("*")).cast("string"),)
    # )
    # CHECKPOINT_LOCATION = "/tmp/checkpoint"

    # result2_1 = (
    #         result_1
    #         .select("value")
    #         .writeStream.trigger(processingTime="10 seconds")
    #         .outputMode("append")
    #         .format("kafka")
    #         .option("topic", "DESTINATION_TOPIC")
    #         .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVER)
    #         .option("checkpointLocation", CHECKPOINT_LOCATION)
    #         .start()
    #         .awaitTermination()
    # )

    # end version 2
    # return query, kafka_query

def acked(err, msg):
    if err is not None:
        print("Failed to deliver message: %s: %s" % (str(msg.value()), str(err)))
    else:
        print("Message produced: %s" % (str(msg.value())))

def produce_result(producer, output_topic, processed_message):
    # Produce the processed message to the output topic
    producer.produce(output_topic, value = json.dumps(str(processed_message)), callback=acked)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preprocessing-topic', 
                        type=str,
                        help='Name of the Kafka topic to receive unprocessed data.')
    parser.add_argument('--model-call-topic', 
                        type=str, 
                        help='Name of the Kafka topic to send preprocessed data to machine learning model.')
    parser.add_argument('--model-response-topic', 
                        type=str, 
                        help='Name of the Kafka topic to receive response from machine learning model.')


    args = parser.parse_args()

    consumer_conf = {'bootstrap.servers': '172.18.0.4:29092',
            'default.topic.config': {'auto.offset.reset': 'smallest'},
            'group.id': socket.gethostname()}
    
    query, kafka_query = msg_process(consumer_conf['bootstrap.servers'], args.preprocessing_topic)
    
    # Define Kafka producer configuration
    producer_conf = {
        'bootstrap.servers': '172.18.0.4:29092',
            'client.id': socket.gethostname(),
            'acks':'all', # continuously prints ack every time a message is sent. but slows process down. 
            'retries':5
    }
    consumer = Consumer(consumer_conf)
    
    # Create Kafka producer for the output topic
    producer = Producer(producer_conf)

    running = True

    try:
        while running:
            consumer.subscribe([args.preprocessing_topic, args.model_response_topic])

            # this script here contains the way to subscribe to multiple topics at the same time:
            # https://stackoverflow.com/questions/72021148/subsrcibe-to-many-topics-in-kafka-using-python

            msg = consumer.poll(1)
            if msg is None:
                # print(f'Oops, {msg.topic()} message is None')
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    sys.stderr.write('%% %s [%d] reached end at offset %d\n' %
                                     (msg.topic(), msg.partition(), msg.offset()))
                elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    sys.stderr.write('Topic unknown, creating %s topic\n' %
                                     (msg.topic()))
                elif msg.error():
                    raise KafkaException(msg.error())
                    break
            else:
                pass
                # sys.stderr.write(f'Received message from {msg.topic()}: {msg.value().decode("utf-8")}')
                # This works, but commenting out because this is not the pattern that we want
                # data={
                #     'user_id': 'a',
                #     'user_name': 'b'
                #     }
                # producer.produce(args.model_call_topic, key = 'patientid', value = json.dumps(data).encode('utf-8'), callback=acked)
                # producer.poll(1)

                # # Flush any pending messages in the producer buffer
                # producer.flush()
                # End this works
    except KeyboardInterrupt:
        query.stop()
        pass

    finally:
        # Close down consumer to commit final offsets.
        consumer.close()
        producer.flush()


# time-series-kafka-demo-processStream-1  | Traceback (most recent call last):
# time-series-kafka-demo-processStream-1  |   File "/home/bin/processStream.py", line 23, in <module>
# time-series-kafka-demo-processStream-1  |     spark = SparkSession.builder.appName('Read CSV File into DataFrame').config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2").getOrCreate()
# time-series-kafka-demo-processStream-1  |   File "/usr/local/lib/python3.9/site-packages/pyspark/sql/session.py", line 269, in getOrCreate
# time-series-kafka-demo-processStream-1  |     sc = SparkContext.getOrCreate(sparkConf)
# time-series-kafka-demo-processStream-1  |   File "/usr/local/lib/python3.9/site-packages/pyspark/context.py", line 483, in getOrCreate
# time-series-kafka-demo-processStream-1  |     SparkContext(conf=conf or SparkConf())
# time-series-kafka-demo-processStream-1  |   File "/usr/local/lib/python3.9/site-packages/pyspark/context.py", line 195, in __init__
# time-series-kafka-demo-processStream-1  |     SparkContext._ensure_initialized(self, gateway=gateway, conf=conf)
# time-series-kafka-demo-processStream-1  |   File "/usr/local/lib/python3.9/site-packages/pyspark/context.py", line 417, in _ensure_initialized
# time-series-kafka-demo-processStream-1  |     SparkContext._gateway = gateway or launch_gateway(conf)
# time-series-kafka-demo-processStream-1  |   File "/usr/local/lib/python3.9/site-packages/pyspark/java_gateway.py", line 106, in launch_gateway
# time-series-kafka-demo-processStream-1  |     raise RuntimeError("Java gateway process exited before sending its port number")
# time-series-kafka-demo-processStream-1  | RuntimeError: Java gateway process exited before sending its port number

if __name__ == "__main__":
    main()
