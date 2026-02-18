from kafka import KafkaProducer
import json

def produce_test_message(broker='localhost:9092', topic='test-topic', key='test-key', value='hello world'):
    producer = KafkaProducer(
        bootstrap_servers=[broker],
        key_serializer=str.encode,
        value_serializer=str.encode
    )
    
    producer.send(topic, key=key, value=value)
    producer.flush()
    print(f'Message sent to topic {topic}: {key} -> {value}')

if __name__ == '__main__':
    produce_test_message()
