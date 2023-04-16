import select
import eventlet
import socketio
from time import sleep

eventlet.monkey_patch()

sio = socketio.Server()
app = socketio.WSGIApp(sio)

label = 'pyMobileDevice'
installation_proxy_service = 'com.apple.mobile.installation_proxy'


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


@sio.on('start_lockdown_service_success')
def on_start_lockdown_service_success(sid, data):
    print(f"[server] start_lockdown_service_success: {data}")

    service_name = data['name']
    if service_name == installation_proxy_service:
        list_app(service_name)


@sio.on('start_lockdown_service_failure')
def on_start_lockdown_service_failure(sid, data):
    print(f"[server] start_lockdown_service_failure: {data}")


@sio.on('service_command_response')
def on_service_command_response(sid, data):
    print(f"[server] service_command_response: {data}")
    getValue()


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



if __name__ == '__main__':
    # export EVENTLET_HUB=poll
    eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 5000)), app)
