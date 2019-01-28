import paho.mqtt.client as mqtt


class MqttListenerClient(object):
    def __init__(self, http_server_input_message_queue, host, port):
        self.http_server_input_message_queue = http_server_input_message_queue
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(host, port)

    def start_listening_on_a_background_thread(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        self.client.subscribe("log/#")

    def _on_message(self, client, userdata, msg):
        self.http_server_input_message_queue.send_message(text = msg.topic+" "+str(msg.payload))
        print(msg.topic+" "+str(msg.payload))

