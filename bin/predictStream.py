import argparse
import wfdb
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
import numpy as np
from utils import evaluate, load_dataset
import torch
from torch import nn
from models import MyCNN
from utils import get_global_config, compute_batch_accuracy, acked, get_producer_config, get_consumer_config, build_spark_session, get_waveform_path, create_batch, get_arr, get_base_time, get_ending_time,get_record,run_model,run_model_dummy
<<<<<<< Updated upstream
from pyspark.sql.functions import explode, split, from_json, to_json, col, struct
=======
from pyspark.sql.functions import explode, split, from_json, to_json, col, struct, window, avg, collect_list,first
>>>>>>> Stashed changes
import pyspark.pandas as ps
import mysql.connector
import datetime
import pandas as pd
from pyspark.sql.types import *

cfg = get_global_config()
cnx = mysql.connector.connect(user='root', 
                              password='mauFJcuf5dhRMQrjj',
                              host='172.18.0.8', 
                              database='mydb')

# Define a function to write each batch of streaming data to MySQL
# This is a placeholder function for now.
def write_to_mysql(batch_df, batch_id):
<<<<<<< Updated upstream
    cursor = cnx.cursor()

    # Convert the batch DataFrame to a list of tuples
    data = [tuple(row) for row in batch_df.collect()]

    # Construct the SQL query to insert the data into MySQL
    query = "INSERT INTO mytable (col1, col2) VALUES (%s, %s)"

    # Insert the data into MySQL using a prepared statement
    cursor.executemany(query, data)
    cnx.commit()
=======

	collected = batch_df.collect()

	# Send results to MySQL
	print(collected)

	# To do: Call ML model on streaming data
>>>>>>> Stashed changes

	# To do: Collect results from ML Model on streaming data

	# To do: Send results to MySQL using the following code:

	# cursor = cnx.cursor()

	# # Convert the batch DataFrame to a list of tuples
	# data = [tuple(row) for row in batch_df.collect()]

	# # Construct the SQL query to insert the data into MySQL
	# query = "INSERT INTO mytable (col1, col2) VALUES (%s, %s)"

	# # Insert the data into MySQL using a prepared statement
	# cursor.executemany(query, data)
	# cnx.commit()

def main():
    spark = build_spark_session()

    """Get arguments from command line"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-call-topic', 
                        type=str,
                        help='Name of the Kafka topic to receive machine learning call.')

    parser.add_argument('--model-response-topic', 
                        type=str,
                        help='Name of the Kafka topic to send the response to the call.')
    
    args = parser.parse_args()

    """Create producer and consumer and interact with kafka"""
    consumer_conf = get_consumer_config()
    producer_conf = get_producer_config()
    producer_conf['kafka.bootstrap.servers'] = producer_conf['bootstrap.servers']
    del producer_conf['bootstrap.servers']

<<<<<<< Updated upstream
    def preprocess_and_send_to_kafka(batch_df, batch_id):
        """The function is fed into foreachBatch of a writestream.
        It preprocesses the data and sends it to Kafka.
        Thus it should be modified for necessary preprocessing"""

        # Preprocess the data
        # Here it does nothing.
        preprocessed_df = batch_df #.select(lower(col("value")).alias("value_lower"))
        
        # Send the preprocessed data to Kafka
        preprocessed_df.write.format("kafka")\
            .options(**producer_conf)\
            .option("topic", "response-stream")\
            .option("value.serializer", "org.apache.kafka.common.serialization.StringSerializer")\
            .option("key.serializer", "org.apache.kafka.common.serialization.StringSerializer")\
            .save()

    def msg_process(server, topic):
        """Create a streaming dataframe that takes in values of messages received, 
        together with the current timestamp.
        Then, print them out.
        Then, process the message in batch
        Reference link: https://medium.com/@aman.parmar17/handling-real-time-kafka-data-streams-using-pyspark-8b6616a3a084"""

        df = (spark.
                readStream
                .format("kafka")
                .option("kafka.bootstrap.servers", server)
                .option("subscribe", topic)
                .option("startingOffsets", "latest")
                .load()
            )
        
        # Select the value and timestamp (the message is received)
        base_df = df.selectExpr("CAST(key as STRING) as key", "CAST(value as STRING)", "timestamp")
        

        # The model needs to be called to store the data
        model = torch.load(cfg['MODELPATH'])
        device = torch.device("cuda" if cfg['USE_CUDA'] and torch.cuda.is_available() else "cpu")

        # Once we manage to set up the actual data, 
        # we will pull data from Kafka stream instead of having to retrieve 
        # data from local.
        data_df = pd.read_csv((cfg['EXPLOREPATH']+'/X.TESTINPUT'))

        # We will also be retrieving the age from the patient_id
        age = 60

        #y_pred, y_prob = run_model(model, device, data_df, age)

        ## to see what "base_df" is like in the stream,
        ## Uncomment base_df.writeStream.outputMode(...)
        ## and comment out base_df.writeStream.foreachBatch(...)
        query = base_df.writeStream.outputMode("append").format("console").trigger(processingTime='10 seconds').start()
        query.awaitTermination()

        ## Write the preprocessed DataFrame to Kafka in batches.
        # kafka_writer: DataStreamWriter = base_df.writeStream.foreachBatch(preprocess_and_send_to_kafka)
        # kafka_query: StreamingQuery = kafka_writer.start()
        # kafka_query.awaitTermination()
        """
        # Write the streaming data to MySQL using foreachBatch
        query = base_df.writeStream.foreachBatch(write_to_mysql).trigger(processingTime='10 seconds').start()
        # query.awaitTermination()
        
        for i in range(10):
            print("Model has successfully run!")
            print(y_pred)
            print(y_prob)
        
        # Store the results in y_pred and y_prob
        # run_model_dummy()
=======
	def msg_process(server, topic):
		"""Create a streaming dataframe that takes in values of messages received, 
		together with the current timestamp.
		Then, print them out.
		Then, process the message in batch
		Reference link: https://medium.com/@aman.parmar17/handling-real-time-kafka-data-streams-using-pyspark-8b6616a3a084"""

		base_df = (spark.
				readStream
				.format("kafka")
				.option("kafka.bootstrap.servers", server)
				.option("subscribe", topic)
				.option("startingOffsets", "latest")
				.load()
			)
		
		# Perform some preprocessing
		base_df = base_df.withColumn("key",col("key").cast("string"))
		base_df = base_df.withColumn("patientid",split(col("key"), '_').getItem(0)) #get patient ID
		base_df = base_df.withColumn("channel",split(col("key"), '_').getItem(1)) #get signal name
		base_df = base_df.withColumn("parsed",from_json(col("value").cast("string"), "array<double>"))

		# In the test case, each window has a duration of 5 seconds. The interval between each window is 2 seconds interval
		# In the actual case, each window has a duration of 10 minutes. The interval between each window is 1 minute interval.
		# The result from the following is suitable for machine learning inference. 
		# This is because each row of the dataframe will contain all the necessary signals for one machine learning input.
		base_df = base_df.withWatermark("timestamp", "3 seconds") \
		.groupBy(
			base_df.patientid,
			window("timestamp", "5 seconds", '2 seconds')) \
		.agg(to_json(struct(first("channel").alias("channel"),collect_list("parsed").alias("lst"))).alias("value2")) \
			.selectExpr(
			"patientid",
			"window.start as start_time",
			"window.end as end_time",
			"value2"
		)

		# Temporarily, to demonstrate that our model can indeed be run, 
		# We will use hard-coded waveform data in the form of a CSV.
		# This is because we have yet to connect the result from hte processStream to the machine learning model.

		# Once we manage to set up the actual data, 
		# we will pull data from Kafka stream instead of having to retrieve 
		# data from local.

		# Retrieve the model
		model = torch.load(cfg['MODELPATH'])
		device = torch.device("cuda" if cfg['USE_CUDA'] and torch.cuda.is_available() else "cpu")

		data_df = pd.read_csv((cfg['EXPLOREPATH']+'/X.TESTINPUT'))

		# We will also be retrieving the age from the patient_id. 
		age = 60
>>>>>>> Stashed changes

        # Create the first cursor for executing queries on the 'mytable' table
        cursor1 = cnx.cursor()
        query1 = 'SELECT * FROM mytable'
        cursor1.execute(query1)
        rows1 = cursor1.fetchall()
        print('Rows from mytable:')
        for idx, row in enumerate(rows1):
            # Too verbose
            if idx %50==0:
                print(row)
            idx+=1
        
        query.awaitTermination()

<<<<<<< Updated upstream
        return query
        """

    query = msg_process(consumer_conf['bootstrap.servers'], args.model_call_topic)
=======
		print("Model has successfully run!")
		print(y_pred)
		print(y_prob)
		
		# Write the streaming data to MySQL using foreachBatch
		query = base_df.writeStream.foreachBatch(write_to_mysql).trigger(processingTime='10 seconds').start()
		
		query.awaitTermination()

		return query

	query = msg_process(consumer_conf['bootstrap.servers'], args.model_call_topic)

	raise Exception
>>>>>>> Stashed changes

if __name__ == "__main__":
    #print("ML module!")
    main()