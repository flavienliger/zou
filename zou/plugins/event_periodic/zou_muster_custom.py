# -*- coding: utf-8 -*-

import os
import re
import json
import requests
import logging
import platform
import time
import base64
from future.utils import iteritems

try:
    from urllib.parse import urlencode
# py2
except:
    from urllib import urlencode

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# -----------------------------
# DEFINE

_muster_info = {
    "8": {
        "address": "muster.ddprs.net",
        "port": "9790",
        "login": "admin",
        "password": "tech1302",
    },
    "9": {
        "address": "dd-muster.ddprs.net",
        "port": "9890",
        "login": "dev",
        "password": "Y5m,Sk>J",
    },
}
MUSTER_VERSION = "9"
FOLDER_ID_2D = 39416
FOLDER_ID_3D = 39417

# ----------------------------

POOLS = []
INSTANCES = []
MUSTER_ACCOUNT = _muster_info[MUSTER_VERSION]
UNIX = platform.system().lower() in ["linux", "darwin"]
project_cache_name = "project_cache{0}.txt".format(
    MUSTER_VERSION != "8" and ("_v" + MUSTER_VERSION + "_2") or ""
)


LAST_PUBLISH = []
MUSTER_SCENE = "//data-pipeline.ddprs.net/muster_repository"
MUSTER_CACHE = "Z:/muster/" + project_cache_name
if UNIX:
    MUSTER_SCENE = "/space/muster_repository"
    MUSTER_CACHE = "/vol/pipeline/muster/" + project_cache_name


# -----------------------------
# UTILS METHOD


def set_windows_path(path):
    # type: (str) -> str
    if path.startswith("/vol/"):
        path = path.replace("/vol/", "/space/")
    if path.startswith("/Volumes/"):
        path = path.replace("/Volumes/", "/space/")
    # TODO: retrieves its information from Muster repositories
    remap = [
        "/space/features",
        "Q:",
        "/space/commercials",
        "O:",
        "/space/commercials/2016",
        "P:",
        "/space/pipeline",
        "Z:",
        "/space/banque",
        "Y:",
        "/space/muster_repository",
        "//data-pipeline/muster_repository",
    ]
    for unix, win in zip(remap[0::2], remap[1::2]):
        path = path.replace(unix, win)
    return path


def read_project_cache(template_type):
    # type: (str) -> dict
    with open(MUSTER_CACHE, "r") as f:
        data = f.read()

    info = {}
    for p in data.split("\n"):
        if not p:
            continue
        splt = p.split(":")
        if template_type == splt[0]:
            info[splt[1]] = splt[2]
    return info


def get_project(path):
    # type: (str) -> Union[str, None]
    path = path.replace("\\", "/")
    splt = path.split("/")

    # q:/project
    if splt[0].lower() in ["o:", "q:", "p:"]:
        # year folder ex: 2016
        if re.match("^20\d{2}$", splt[1]):
            return splt[2]
        return splt[1]

    elif splt[0].lower() in ["y:"]:
        return "RnD"

    # /space/server/project
    elif splt[0] == "":
        # year folder ex: 2016
        if re.match("^20\d{2}$", splt[3]):
            return splt[4]
        return splt[3]

    return None


def remove_specific_project_cache(search_line):
    with open(MUSTER_CACHE) as file_handle:
        lines = file_handle.readlines()

    for i, line in enumerate(lines):
        if line == search_line:
            del lines[i]
            break

    with open(MUSTER_CACHE, "w") as file_handle:
        file_handle.writelines(lines)


# -----------------------------
# MUSTER CLASS


class ConstData(object):
    data = {}

    def __getitem__(self, id):
        for key, val in iteritems(self.data):
            if val == id:
                return key
        return None


class JobPacketType(ConstData):
    MULTIFRAME, IMAGESLICING, BROADCAST, SINGLECOMMAND, MULTITASK = (
        lambda: [2 ** x for x in range(5)]
    )()
    data = {
        n: 2 ** i
        for i, n in enumerate(
            ["MULTIFRAME", "IMAGESLICING", "BROADCAST", "SINGLECOMMAND", "MULTITASK"]
        )
    }


class JobType(ConstData):
    """The different types of jobs"""

    JOB, FOLDER = range(2)
    data = {"JOB": 1, "FOLDER": 2}


class DependMode(ConstData):
    """The different types of dependency modes between jobs"""

    (SUCCESS_REQUIRED, ACCEPT_WARNING, ACCEPT_ERRORS) = (
        lambda: [x for x in range(3)]
    )()
    order = ["SUCCESS_REQUIRED", "ACCEPT_WARNING", "ACCEPT_ERRORS"]
    data = {n: i for i, n in enumerate(order)}


class ChunksStatus(ConstData):
    (ON_HOLD, SUBMITTED, COMPLETED, WARNING, ERROR) = (
        lambda: [2 ** x for x in range(5)]
    )()
    data = {
        n: 2 ** i
        for i, n in enumerate(["ON_HOLD", "SUBMITTED", "COMPLETED", "WARNING", "ERROR"])
    }


class JobStatus(ConstData):
    """The different jobs status"""

    (
        ON_QUEUE,
        STARTED,
        IN_PROGRESS_WARNINGS,
        IN_PROGRESS_ERRORS,
        PRE_JOB_ACTION,
        POST_JOB_ACTION,
        PENDING_PRE_JOB_ACTION,
        PENDING_POST_JOB_ACTION,
        PENDING_FRAME_CHECK,
        FRAME_CHECK,
        JOB_COMPLETED,
        COMPLETED_WITH_WARNINGS,
        COMPLETED_WITH_ERRORS,
        PENDING_POST_JOB_PY_ACTION,
        POST_JOB_PY_ACTION,
        LOCKED,
        ARCHIVED,
        PAUSED,
    ) = (lambda: [2 ** x for x in range(18)])()
    data = {
        n: 2 ** i
        for i, n in enumerate(
            [
                "ON_QUEUE",
                "STARTED",
                "IN_PROGRESS_WARNINGS",
                "IN_PROGRESS_ERRORS",
                "PRE_JOB_ACTION",
                "POST_JOB_ACTION",
                "PENDING_PRE_JOB_ACTION",
                "PENDING_POST_JOB_ACTION",
                "PENDING_FRAME_CHECK",
                "FRAME_CHECK",
                "JOB_COMPLETED",
                "COMPLETED_WITH_WARNINGS",
                "COMPLETED_WITH_ERRORS",
                "PENDING_POST_JOB_PY_ACTION",
                "POST_JOB_PY_ACTION",
                "LOCKED",
                "ARCHIVED",
                "PAUSED",
            ]
        )
    }


class MusterInfo:
    JOB_PACKET_TYPE = JobPacketType()
    JOB_TYPE = JobType()
    DEPEND_MODE = DependMode()
    JOB_STATUS = JobStatus()
    CHUNKS_STATUS = ChunksStatus()


MUSTER = MusterInfo()

# -----------------------------
# MUSTER REST API


class MusterManager(object):
    def __init__(
        self,
        username,
        password,
        address=MUSTER_ACCOUNT["address"],
        port=MUSTER_ACCOUNT["port"],
        auto_login=False,
    ):
        # type: (str, str, str, str, bool) -> None
        self.username = username
        self.password = password
        self.is_connected = False
        self._server_url = "http://{address}:{port}/".format(address=address, port=port)
        self._auth_token = None

        # set requests logging level
        logging.getLogger("requests").setLevel(logging.WARN)

        self.client = requests.session()
        self._login_try = 0
        self._max_login_try = 10

        if auto_login:
            self.login()

    def login(self, reconnect=False):
        # type: (bool) -> Union[bool, str]
        user = {"userName": self.username, "password": self.password}
        login_url = "{server_url}api/login?{user}".format(
            server_url=self._server_url, user=urlencode(user)
        )
        self._login_try += 1

        try:
            resp = self.client.get(login_url)
            resp.raise_for_status()
            json_response = json.loads(resp.text)
            self._auth_token = json_response["ResponseData"]["authToken"]
            self.is_connected = True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.exception("Unknown user login {0}".format(self.username))
                return "Failed to login"
        except:
            logger.exception("Failed to connect")
            if not reconnect:
                return "Failed to connect"
            if self._login_try > self._max_login_try:
                return "Failed to connect too many attempts"
            time.sleep(60)
            return self.login(reconnect)

        return False

    def logout(self):
        # type: () -> None
        if not self.is_connected:
            return

        logout_url = "{server_url}api/logout?authToken={token}".format(
            server_url=self._server_url, token=self._auth_token
        )

        try:
            resp = self.client.get(logout_url)
            resp.raise_for_status()
            self.is_connected = False
        except:
            logger.exception("Failed to disconnect")

    def _send_actions_request(self, action_name, data):
        # type: (str, dict) -> dict
        resp = self.client.post(
            self._server_url + "api/queue/actions",
            headers={"Content-Type": "application/json"},
            params=(("authToken", self._auth_token), ("name", action_name)),
            data=json.dumps(data),
        )

        resp_data = resp.json()
        return resp_data

    def send_kill_and_pause(self, job_id):
        # type: (int) -> Dict
        return self._send_actions_request(
            "killAndPause", {"RequestData": {"jobId": job_id}}
        )

    def get_job_by_id(self, job_id):
        # type: (int) -> Union[dict, None]
        resp = self.client.post(
            self._server_url + "api/queue/list",
            headers={"Content-Type": "application/json"},
            params=(
                ("authToken", self._auth_token),
                ("filter", "jobId:{0}".format(job_id)),
            ),
        )

        resp_data = resp.json()
        data = resp_data.get("ResponseData", {})
        queue = data.get("queue", [])

        if queue.__len__() > 0:
            q = queue[0]
            q.update(
                {
                    "statusId": q.get("status"),
                    "status": MUSTER.JOB_STATUS[q.get("status")],
                }
            )

            attr_upd = {}
            for key, attr in iteritems(q.get("attributes", {})):
                attr_upd[key] = attr.get("value")
            q.update(attr_upd)

            return q
        return None

    def requeue_chunk(self, job_id, chunk_id):
        # type: (int, int) -> Bool
        data = {"RequestData": {"jobId": job_id, "chunkId": chunk_id}}
        resp = self.client.post(
            self._server_url + "api/chunks/actions",
            headers={"Content-Type": "application/json"},
            params=(("authToken", self._auth_token), ("name", "setOnHold")),
            data=json.dumps(data),
        )
        return resp.ok

    def get_chunks_by_jobid(self, job_id):
        # type: (int) -> Union[dict, None]
        resp = self.client.post(
            self._server_url + "api/chunks/list",
            headers={"Content-Type": "application/json"},
            params=(
                ("authToken", self._auth_token),
                ("filter", "jobId:{0}".format(job_id)),
            ),
        )

        resp_data = resp.json()
        data = resp_data.get("ResponseData", {})
        queue = data.get("chunks", [])

        if queue.__len__() > 0:
            for q in queue:
                q.update(
                    {
                        "statusId": q.get("status"),
                        "status": MUSTER.CHUNKS_STATUS[q.get("status")],
                    }
                )

            return queue
        return None

    def send_job(self, job, job_type=MUSTER.JOB_TYPE.JOB, job_owner=None):
        # type: (dict, int, str) -> Union[int, None]
        if job_type == MUSTER.JOB_TYPE.JOB:
            data = {"RequestData": {"job": job}}
            action_name = "submit"

        elif job_type == MUSTER.JOB_TYPE.FOLDER:
            data = {"RequestData": job}
            action_name = "createFolder"

        resp_data = self._send_actions_request(action_name, data)

        logger.debug("Data: %s" % resp_data)

        # get the id of the job sent, from the output
        job_id = resp_data.get("ResponseStatus").get("objectId")

        if not job_id:
            logger.exception("Launching job failed. Job data: {data}".format(data=data))
            return None

        logger.info("Job sent with id : " + str(job_id))

        # edit job to change owner
        if job_owner and job_owner != self.username:
            self.edit_job_owner(job_id, job_owner)

        return int(job_id)

    def edit_job_owner(self, job_id, job_owner):
        # type: (int, str) -> None
        data = {
            "RequestData": {
                "jobId": job_id,
                "owner": "@directory@{username}".format(username=job_owner),
            }
        }
        resp = self._send_actions_request("setOwner", data)
        logger.debug("Edit owner: {0}".format(resp))

    def send_pause_job(self, job_id):
        # type: (int) -> dict
        return self._send_actions_request("pause", {"RequestData": {"jobId": job_id}})

    def send_resume_job(self, job_id):
        # type: (int) -> dict
        return self._send_actions_request("resume", {"RequestData": {"jobId": job_id}})

    def send_remove_job(self, job_id):
        # type: (int) -> dict
        # ", ".join(map(str, job_ids))
        return self._send_actions_request("remove", {"RequestData": {"jobId": job_id}})

    def create_folder(
        self,
        folder_name,
        priority=100,
        parent_id=-1,
        type_project=None,
        save_project=False,
    ):
        # type: (str, int, int, str, bool) -> Union[int, None]
        send_job_options = {
            "folderName": folder_name,
            "priority": priority,
            "parentId": parent_id,
        }

        # creation by admin account
        if save_project:
            admin_session = MusterManager(
                MUSTER_ACCOUNT["login"], MUSTER_ACCOUNT["password"]
            )
            # try auth
            if admin_session.login():
                return None

            job_id = admin_session.send_job(send_job_options, MUSTER.JOB_TYPE.FOLDER)
            admin_session.logout()

            if not job_id:
                return None

            # remove existing project
            with open(MUSTER_CACHE, "a") as f:
                f.write("{0}:{1}:{2}\n".format(type_project, folder_name, job_id))

        else:
            job_id = self.send_job(send_job_options, MUSTER.JOB_TYPE.FOLDER)

        return job_id

    def get_pools(self):
        # type: () -> list
        global POOLS

        if POOLS:
            return POOLS

        request = self.client.post(
            url=self._server_url + "api/pools/list",
            data={"authToken": self._auth_token},
        )

        pools_json = json.loads(request.text)["ResponseData"]["pools"]
        POOLS = sorted([pool["name"] for pool in pools_json])
        return POOLS

    def get_project_id(self, type_project, project_name):
        # type: (str, str) -> Union[int, None]
        projects = read_project_cache(type_project)

        for key, id in iteritems(projects):
            if key.lower() == project_name.lower():
                # verify if id is right
                if not self.get_job_by_id(id):
                    remove_specific_project_cache(
                        "{0}:{1}:{2}\n".format(type_project, key, id)
                    )
                    break
                else:
                    return id

        # not already created
        template_id = type_project == "2D" and FOLDER_ID_2D or FOLDER_ID_3D
        return self.create_folder(
            project_name,
            parent_id=template_id,
            type_project=type_project,
            save_project=True,
        )

    def get_instances(self):
        # type: () -> list
        global INSTANCES

        if INSTANCES:
            return INSTANCES

        request = self.client.post(
            url=self._server_url + "api/instances/list",
            data={"authToken": self._auth_token},
        )

        instances_json = json.loads(request.text)["ResponseData"]["instances"]
        # TODO: check if is hostName or instanceName
        INSTANCES = sorted([pool["hostName"] for pool in instances_json])
        return INSTANCES

    def get_job_frame_check(self, options={}):
        return {}

    def get_job_args(self, options):
        # type: (dict) -> dict
        muster_var = {
            "jobName": "job_name",
            "priority": "job_priority",
            "packetSize": "packet_size",
            "templateId": "template_id",
            "includedPools": "included_pools",
            "excludedPools": "excluded_pools",
            "maximumInstances": "job_max_instances",
            "parentId": "job_parent",
            "project": "job_project",
            "department": "job_department",
            "dependIds": "job_deps",
            "dependMode": "job_deps_mode",
            "pauseOn": "job_pause",
            "overrideMinimumRam": "job_minimum_ram",
            "overrideMinimumRamValue": "job_minimum_ram_value",
        }

        job = {}

        for key, val in iteritems(muster_var):
            v = options.get(val)
            if not v:
                continue

            if key in ["includedPools", "excludedPools", "dependIds"]:
                if type(v) in [str, int]:
                    v = [e.strip() for e in str(v).split(",")]

            elif key in ["pauseOn"]:
                v = v and "1" or "0"

            elif key in ["dependMode"]:
                depend_text = MUSTER.DEPEND_MODE.order[v]
                v = MUSTER.DEPEND_MODE.data[depend_text]

            job[key] = v

        return job

    def get_job_args_template(self, custom_options, options={}, windows_path=True):
        # type: (dict, dict, bool) -> dict
        muster_var_custom = {
            "job_file": "job_file",
            "start_frame": "start_frame",
            "end_frame": "end_frame",
            "by_frame": "by_frame",
            "frames_range": "frames_range",
            "frames_mask": "frames_mask",
        }

        for key, val in iteritems(muster_var_custom):
            if options.get(val):
                custom_options[key] = options.get(val)

        # Muster 9 notation
        start_frame = options.get("start_frame", None)
        end_frame = options.get("end_frame", None)
        by_frame = options.get("by_frame", 1)

        if (
            MUSTER_VERSION == "9"
            and not options.get("frames_range")
            and start_frame is not None
            and end_frame is not None
        ):
            custom_options["frames_range"] = "{0}-{1}x{2}".format(
                start_frame, end_frame, by_frame
            )

        job = {"attributes": {}}
        for key, val in iteritems(custom_options):
            val = str(val)
            subst = False

            if windows_path and "/" in val or "\\" in val:
                val = set_windows_path(val)

            if key == "frames_mask":
                val = base64.b64encode(val + "\n")
                subst = True

            job["attributes"][key] = {"value": val, "state": True, "subst": subst}
        return job
