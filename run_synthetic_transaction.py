import re
import json
import time

import datadog
import requests


BOOL_TO_BIN = {True: 1, False: 0}

'''
These are more likely to be exposed as an environment variables
but for simplicity, they are hardcoded
'''
datadog.initialize(**{
    'api_key': '',
    'app_key': ''})

def report_results(availability, latency, correctness):
    print("Availability: {}, latency: {}, correctness: {}".format(
        availability, latency, correctness))

    # Report availability
    datadog.statsd.gauge('synthetic_test.job_name.availability', availability)

    # Report correctness
    datadog.statsd.gauge('synthetic_test.job_name.correctness', correctness)

    # Report latency
    datadog.statsd.distribution('synthetic_test.job_name.latency', latency)


class TamagotchiSyntheticMonitor(object):
    def __init__(self, conf):
        self.conf = conf
        print(json.dumps(conf, indent=4, sort_keys=True))

    def _synthetic_transaction(self):
        start_time = time.time()
        resp = requests.request(
            self.conf["request"]["method"],
            self.conf["request"]["url"],
            headers=self.conf["request"]["headers"],
            data=self.conf["request"]["body"])
        latency = time.time() - start_time
        return resp, latency

    def _get_availability_val(self, resp):
        available_statuses = self.conf["validations"][
            "status_codes_service_available"]
        return BOOL_TO_BIN[resp.status_code in available_statuses]

    def _get_correctness_val(self, resp):
        regex = self.conf["validations"]["validate_body_regex"]
        if regex:
            return BOOL_TO_BIN[re.match(resp.body, regex)]
        return 1

    def run_test(self):
        resp, latency = self._synthetic_transaction()
        availability = self._get_availability_val(resp)
        correctness = self._get_correctness_val(resp)

        report_results(availability, latency, correctness)


'''
Conf file is expected to be mounted as part of the docker exec.
More likely conf name will be something like JOB_ID.conf and
we will take it from an env variable or something similar
'''
def parse_conf():
    with open("tamagotchi.conf") as f:
        return json.load(f)


if __name__ == '__main__':
    t = TamagotchiSyntheticMonitor(parse_conf())
    while True:
        t.run_test()
        time.sleep(30)
