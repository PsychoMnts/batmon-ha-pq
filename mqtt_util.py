import json

import paho.mqtt.client as paho

from bmslib.bms import BmsSample
from util import get_logger

logger = get_logger()


def build_mqtt_hass_config_discovery(base, topic):
    # Instead of daly_bms should be here added a proper name (unique), like serial or something
    # At this point it can be used only one daly_bms system with hass discovery

    hass_config_topic = f'homeassistant/sensor/{topic}/{base.replace("/", "_")}/config'
    hass_config_data = {}

    hass_config_data["unique_id"] = f'{topic}_{base.replace("/", "_")}'
    hass_config_data["name"] = f'{topic} {base.replace("/", " ")}'

    # see https://www.home-assistant.io/integrations/sensor/

    if 'soc_percent' in base or base.endswith('/soc'):
        hass_config_data["device_class"] = 'battery'
        hass_config_data["unit_of_measurement"] = '%'
    elif 'voltage' in base:
        hass_config_data["device_class"] = 'voltage'
        hass_config_data["unit_of_measurement"] = 'V'
    elif 'current' in base:
        hass_config_data["device_class"] = 'current'
        hass_config_data["unit_of_measurement"] = 'A'
    elif 'power' in base:
        hass_config_data["device_class"] = 'power'
        hass_config_data["unit_of_measurement"] = 'W'
    elif 'capacity' in base or base.endswith('/charge'):
        # hass_config_data["device_class"] = ''
        hass_config_data["unit_of_measurement"] = 'Ah'
    elif 'temperatures' in base:
        hass_config_data["device_class"] = 'temperature'
        hass_config_data["unit_of_measurement"] = '°C'
    else:
        pass

    hass_config_data["json_attributes_topic"] = f'{topic}{base}'
    hass_config_data["state_topic"] = f'{topic}{base}'

    hass_device = {
        "identifiers": [topic],  # daly_bms
        "manufacturer": topic,  # Daly
        "model": 'Currently not available',
        "name": topic,  # Daly BMS
        "sw_version": 'Currently not available'
    }
    hass_config_data["device"] = hass_device

    return hass_config_topic, json.dumps(hass_config_data)


def mqtt_single_out(client: paho.Client, topic, data, retain=False):
    # logger.debug(f'Send data: {data} on topic: {topic}, retain flag: {retain}')
    print('mqtt: ' + topic, data)
    return
    mqi: paho.MQTTMessageInfo = client.publish(topic, data, retain=retain)
    if mqi.rc != paho.MQTT_ERR_SUCCESS:
        logger.warning('mqtt publish %s failed: %s', topic, mqi)
    if not mqi.is_published():
        logger.warning('mqtt msg %s not published: %s', topic, mqi)


def mqtt_iterator(client, result, topic, base='', hass=True):
    for key in result.keys():
        if type(result[key]) == dict:
            mqtt_iterator(client, result[key], topic, f'{base}/{key}', hass)
        else:
            if hass:
                # logger.debug('Sending out hass discovery message')
                topic_, output = build_mqtt_hass_config_discovery(f'{base}/{key}', topic=topic)
                mqtt_single_out(client, topic_, output, retain=True)

            if type(result[key]) == list:
                val = json.dumps(result[key])
            else:
                val = result[key]

            mqtt_single_out(client, f'{topic}{base}/{key}', val)


sample_desc = {
    "soc/total_voltage": {"field": "voltage", "class": "voltage", "unit_of_measurement": "V"},
    "soc/current": {"field": "current", "class": "current", "unit_of_measurement": "A"},
    "soc/soc_percent": {"field": "soc", "class": "battery", "unit_of_measurement": "%"},
    "mosfet_status/capacity_ah": {"field": "charge", "class": None, "unit_of_measurement": "Ah"},
}


def publish_sample(client, device_topic, sample: BmsSample):
    for k, v in sample_desc.items():
        topic = f"{device_topic}/{k}"
        mqtt_single_out(client, topic, getattr(sample, v['field']))

def publish_cell_voltages(client, device_topic, voltages):
    for i in range(0, len(voltages)):
        topic = f"{device_topic}/cell_voltages/{i}"
        mqtt_single_out(client, topic, voltages[i]/1000)

def publish_hass_discovery(client, device_topic, num_cells):

    discovery_msg = {}

    def _hass_discovery(k, device_class, unit):
        discovery_msg[f"homeassistant/sensor/{device_topic}/_{k.replace('/', '_')}/config"] = {
            "unique_id": f"{device_topic}__{k.replace('/', '_')}",
            "name": f"{device_topic} {k.replace('/', ' ')}",
            "device_class": device_class or "",
            "unit_of_measurement": unit,
            "json_attributes_topic": f"{device_topic}/{k}",
            "state_topic": f"{device_topic}/{k}",
            "device": {
                "identifiers": [device_topic],  # daly_bms
                "manufacturer": device_topic,  # Daly
                "model": 'Currently not available',
                "name": device_topic,  # Daly BMS
                "sw_version": 'Currently not available'
            },
        }

    for k, d in sample_desc.items():
        _hass_discovery(k, d["class"], unit=d["unit_of_measurement"])

    for i in range(0, num_cells):
        k = 'cell_voltages/%d' % i
        _hass_discovery(k, "voltage", unit="V")

    for topic, data in discovery_msg.items():
        mqtt_single_out(client, topic, data)

    """
    

mqtt: homeassistant/sensor/daly_bms/_status_temperature_sensors/config {"unique_id": "daly_bms__status_temperature_sensors", "name": "Daly BMS  status temperature_sensors", "json_attributes_topic": "daly_bms/status/temperature_sensors", "state_topic": "daly_bms/status/temperature_sensors", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/status/temperature_sensors 1
mqtt: homeassistant/sensor/daly_bms/_status_charger_running/config {"unique_id": "daly_bms__status_charger_running", "name": "Daly BMS  status charger_running", "json_attributes_topic": "daly_bms/status/charger_running", "state_topic": "daly_bms/status/charger_running", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/status/charger_running False
mqtt: homeassistant/sensor/daly_bms/_status_load_running/config {"unique_id": "daly_bms__status_load_running", "name": "Daly BMS  status load_running", "json_attributes_topic": "daly_bms/status/load_running", "state_topic": "daly_bms/status/load_running", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/status/load_running False
mqtt: homeassistant/sensor/daly_bms/_status_states_DI1/config {"unique_id": "daly_bms__status_states_DI1", "name": "Daly BMS  status states DI1", "json_attributes_topic": "daly_bms/status/states/DI1", "state_topic": "daly_bms/status/states/DI1", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/status/states/DI1 False
mqtt: homeassistant/sensor/daly_bms/_status_states_DI2/config {"unique_id": "daly_bms__status_states_DI2", "name": "Daly BMS  status states DI2", "json_attributes_topic": "daly_bms/status/states/DI2", "state_topic": "daly_bms/status/states/DI2", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/status/states/DI2 True
mqtt: homeassistant/sensor/daly_bms/_status_cycles/config {"unique_id": "daly_bms__status_cycles", "name": "Daly BMS  status cycles", "json_attributes_topic": "daly_bms/status/cycles", "state_topic": "daly_bms/status/cycles", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/status/cycles 5
mqtt: homeassistant/sensor/daly_bms/_cell_voltages_1/config {"unique_id": "daly_bms__cell_voltages_1", "name": "Daly BMS  cell_voltages 1", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/cell_voltages/1", "state_topic": "daly_bms/cell_voltages/1", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/cell_voltages/1 3.325
mqtt: homeassistant/sensor/daly_bms/_cell_voltages_2/config {"unique_id": "daly_bms__cell_voltages_2", "name": "Daly BMS  cell_voltages 2", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/cell_voltages/2", "state_topic": "daly_bms/cell_voltages/2", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/cell_voltages/2 3.331
mqtt: homeassistant/sensor/daly_bms/_cell_voltages_3/config {"unique_id": "daly_bms__cell_voltages_3", "name": "Daly BMS  cell_voltages 3", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/cell_voltages/3", "state_topic": "daly_bms/cell_voltages/3", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/cell_voltages/3 3.301
mqtt: homeassistant/sensor/daly_bms/_cell_voltages_4/config {"unique_id": "daly_bms__cell_voltages_4", "name": "Daly BMS  cell_voltages 4", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/cell_voltages/4", "state_topic": "daly_bms/cell_voltages/4", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/cell_voltages/4 3.331
mqtt: homeassistant/sensor/daly_bms/_cell_voltages_5/config {"unique_id": "daly_bms__cell_voltages_5", "name": "Daly BMS  cell_voltages 5", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/cell_voltages/5", "state_topic": "daly_bms/cell_voltages/5", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/cell_voltages/5 3.331
mqtt: homeassistant/sensor/daly_bms/_cell_voltages_6/config {"unique_id": "daly_bms__cell_voltages_6", "name": "Daly BMS  cell_voltages 6", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/cell_voltages/6", "state_topic": "daly_bms/cell_voltages/6", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/cell_voltages/6 3.324
mqtt: homeassistant/sensor/daly_bms/_cell_voltages_7/config {"unique_id": "daly_bms__cell_voltages_7", "name": "Daly BMS  cell_voltages 7", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/cell_voltages/7", "state_topic": "daly_bms/cell_voltages/7", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/cell_voltages/7 3.328
mqtt: homeassistant/sensor/daly_bms/_cell_voltages_8/config {"unique_id": "daly_bms__cell_voltages_8", "name": "Daly BMS  cell_voltages 8", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/cell_voltages/8", "state_topic": "daly_bms/cell_voltages/8", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/cell_voltages/8 3.323
mqtt: homeassistant/sensor/daly_bms/_balancing_status_error/config {"unique_id": "daly_bms__balancing_status_error", "name": "Daly BMS  balancing_status error", "json_attributes_topic": "daly_bms/balancing_status/error", "state_topic": "daly_bms/balancing_status/error", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/balancing_status/error not implemented
mqtt: homeassistant/sensor/daly_bms/_errors/config {"unique_id": "daly_bms__errors", "name": "Daly BMS  errors", "json_attributes_topic": "daly_bms/errors", "state_topic": "daly_bms/errors", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/errors []
    
    mqtt: homeassistant/sensor/daly_bms/_soc_total_voltage/config {"unique_id": "daly_bms__homeassistant/sensor/daly_bms/_soc_total_voltage/config {"unique_id": "daly_bms__soc_total_voltagesoc_total_voltage", "name": "Daly BMS  soc total_voltage", "device_class": "voltage", "unit_of_measurement": "V", "json_attributes_topic": "daly_bms/soc/total_voltage", "state_topic": "daly_bms/soc/total_voltage", "device": {"identifiers": ["daly_bms"], "manufacturer": "Daly", "model": "Currently not available", "name": "Daly BMS", "sw_version": "Currently not available"}}
mqtt: daly_bms/soc/total_voltage 26.5

    
    :return: 
    """
