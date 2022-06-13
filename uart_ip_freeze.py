#!/usr/bin/env python3

import serial
import serial.tools.list_ports as port_list
import time

BAUD = 115200
QUERY = "ifconfig\n"
IP_START = "192.168."
INTERFACE = "wlan0"
USER = "root"
PASS = "0hanah0me"
MAX_MSG_LEN = 2048
serial_port = None


def open_device(dev_port):
    global serial_port

    serial_port = serial.Serial(port=dev_port, baudrate=BAUD, bytesize=8, timeout=0.1, stopbits=serial.STOPBITS_ONE)


def close_device():
    global serial_port

    serial_port.close()


def set_device_timeout(timeout):
    global serial_port

    serial_port.timeout = timeout


def wait_for_device_idle():
    global serial_port

    set_device_timeout(3)
    dev_msg = ""
    response = serial_port.read(1024).decode("utf-8")
    dev_msg += response
    while len(response) > 0:
        response = serial_port.read(1024).decode("utf-8")
        dev_msg += response

    if len(dev_msg) < len("password:"):
        # message received is too short to determine current state. Provoke the device to say more.
        serial_port.write("\n".encode("utf-8"))
        response = serial_port.read(1024).decode("utf-8")
        dev_msg += response

    print("Device response 1: {}".format(dev_msg))

    # Board is now idle. We only need the last message row.
    dev_msg = dev_msg.split('\n')[-1]

    # Check if login is required.
    if "password:" in dev_msg.lower():
        # Password required, but we did not send correct login, so skip this.
        set_device_timeout(7)
        serial_port.write("\n".encode("utf-8"))
        dev_msg = serial_port.read(1024).decode("utf-8")
        print("Device response 2: {}".format(dev_msg))

    set_device_timeout(3)
    if "login:" in dev_msg:
        print('Sending login')
        serial_port.write("{}\n".format(USER).encode("utf-8"))
        dev_msg = serial_port.read(1024).decode("utf-8")
        print("Device response login: {}".format(dev_msg))

        if "password:" in dev_msg.lower():
            print('Sending pass')
            set_device_timeout(7)
            serial_port.write("{}\n".format(PASS).encode("utf-8"))

    response = serial_port.read(1024).decode("utf-8")
    print("Device response: {}".format(response))


def set_device_ip(dev_port, target_ip):
    global serial_port

    set_msg = "ifconfig {} {}\n".format(INTERFACE, target_ip)
    serial_port.write(set_msg.encode("utf-8"))
    serial_port.read(1024)
    serial_port.close()


def query_device_ip():
    global serial_port

    serial_port.write(QUERY.encode("utf-8"))
    response = serial_port.read(1024).decode('utf-8')
    return response


def get_dev_ip(dev_port):
    open_device(dev_port)
    wait_for_device_idle()
    response = query_device_ip()
    close_device()

    interface = ""
    for line in response.split('\n'):
        info = line.split(':')
        if len(info) > 1 and "flags" in info[1]:
            interface = info[0]

        if INTERFACE in interface:
            data = line.strip()

            if IP_START in data:
                # This is the IP address line we are looking for
                info = data.split(' ')
                for segment in info:
                    if IP_START in segment:
                        return segment

    return None


def list_uart_devices():
    device_dict = {}

    ports = list(port_list.comports())
    for one_port in ports:
        port = one_port.device
        ip_addr = get_dev_ip(port)
        if ip_addr is not None:
            device_dict["port"] = ip_addr

    return device_dict


initial_devices = list_uart_devices()
print("Found: {}".format(initial_devices))

while True:
    time.sleep(10)
    devices = list_uart_devices()

    for device_port in initial_devices.keys():
        current_dev_ip = devices.get(device_port, None)
        initial_dev_ip = initial_devices.get(device_port)

        if current_dev_ip is not None and current_dev_ip != initial_dev_ip:
            set_device_ip(device_port, initial_dev_ip)
