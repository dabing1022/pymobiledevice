import os.path
import select
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


def wait_for_input():
    while True:
        user_input = input("Please enter your command: \n")
        if user_input == "quit":
            break
        elif "start_lockdown_service" in user_input:
            service_name = user_input.split(" ")[1]
            start_lockdown_service(service_name)
        else:
            print("Unknown command:", user_input)


# start_lockdown_service com.apple.mobile.installation_proxy
if __name__ == '__main__':
    start_server()