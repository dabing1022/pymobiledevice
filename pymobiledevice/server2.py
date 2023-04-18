import os.path
import select
from cmd import Cmd

import eventlet
import socketio
from time import sleep, strftime, gmtime
import threading
import multiprocessing
import tempfile

eventlet.monkey_patch()

sio = socketio.Server(max_http_buffer_size=100e6)
app = socketio.WSGIApp(sio)

label = 'pyMobileDevice'
installation_proxy_service = 'com.apple.mobile.installation_proxy'
screenshotr_service = 'com.apple.mobile.screenshotr'

queue = multiprocessing.Queue()

@sio.event
def connect(sid, environ):
    print('connect ', sid)


@sio.event
def disconnect(sid):
    print('disconnect ', sid)


@sio.on('lockdown_client_connected')
def on_lockdown_client_connected(sid, data):
    print(f"[server] lockdown_client_connected: {data}")

    start_lockdown_service(installation_proxy_service)

    # start_lockdown_service(screenshotr_service)



@sio.on('start_lockdown_service_success')
def on_start_lockdown_service_success(sid, data):
    print(f"[server] start_lockdown_service_success: {data}")

    start_lockdown_service(screenshotr_service)

    service_name = data['name']
    if service_name == installation_proxy_service:
        list_app(service_name)
    elif service_name == screenshotr_service:
        take_screenshot(service_name)


@sio.on('start_lockdown_service_failure')
def on_start_lockdown_service_failure(sid, data):
    print(f"[server] start_lockdown_service_failure: {data}")


@sio.on('service_command_response')
def on_service_command_response(sid, data):
    service_name = data['name']
    print(f"[server] service_command_response: {service_name}")
    if service_name == screenshotr_service:
        res = data['response']
        assert len(res) == 2
        assert res[0] == "DLMessageProcessMessage"

        tiff_dir = os.path.expanduser("~/Downloads/Screenshots")
        filename = strftime('screenshot-%Y-%m-%d-%H-%M-%S.tiff', gmtime())
        if not os.path.exists(tiff_dir):
            os.makedirs(tiff_dir)
        tiff_file_path = os.path.join(tiff_dir, filename)

        if res[1].get('MessageType') == 'ScreenShotReply':
            screen_data = res[1]['ScreenShotData']
            with open(tiff_file_path, "wb") as fd:
                fd.write(screen_data)
                print(f"[server] screenshot saved to {tiff_file_path}")
    else:
       # getValue()
       # 查询是否处于监管模式
       getValue(domain='com.apple.mobile.chaperone', key='DeviceIsChaperoned')


@sio.on('common_response')
def on_common_response(sid, data):
    print(f"[server] common_response: {data}")


def start_lockdown_service(name: str):
    print(f"[server] start lockdown service: {name}")
    payload = {"Label": label, "Request": "StartService", "Service": name}
    sio.emit('start_lockdown_service', payload)


def list_app(service_name):
    print(f"[server] list app")
    payload = {"service": service_name, "command": {"Command": "Lookup"}}
    sio.emit('service_command_request', payload)

def list_app_queue(service_name):
    print(f"[server] list app")
    payload = {"service": service_name, "command": {"Command": "Lookup"}}
    queue.put(payload)

def getValue(domain=None, key=None):
    print(f"[server] getValue: {domain} {key}")
    payload = {"Label": label, "Request": "GetValue"}
    if domain:
        payload["Domain"] = domain
    if key:
        payload["Key"] = key
    sio.emit('common_request', payload)


def take_screenshot(service_name):
    print(f"[server] take screenshot")
    payload = {"service": service_name, "command": ['DLMessageProcessMessage', {'MessageType': 'ScreenShotRequest'}]}
    sio.emit('service_command_request', payload)


def start_server():
    # export EVENTLET_HUB=poll
    eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 5000)), app)

def start_server_aync():
    eventlet.greenthread.spawn(handle_queue_message)
    eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 5000)), app)


def handle_queue_message():
    print("handle_queue_message")
    while True:
        if not queue.empty():
            message = queue.get()
            print("handle_queue_message", message)
            sio.emit('service_command_request', message)
        sleep(0.5)


class ServerShell(Cmd):

    def __init__(self, completekey='tab', stdin=None, stdout=None):
        Cmd.__init__(self, completekey=completekey, stdin=stdin, stdout=stdout)
        self.curdir = '/'
        self.prompt = 'USB/IP Server$ ' + self.curdir + ' '

    def do_test(self, p):
        print(f"print test {p}")


    def do_start_server(self, p):
        print(f"print start server {p}")
        p = multiprocessing.Process(target=start_server_aync)
        p.start()

    def do_start_service(self, p):
        print(f"print start service {p}")
        start_lockdown_service(p)

    def do_list_app(self, p):
        print(f"print list app {p}")
        list_app_queue(p)




# start_lockdown_service com.apple.mobile.installation_proxy
if __name__ == '__main__':
    server_cell = ServerShell()
    server_cell.cmdloop()