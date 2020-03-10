import threading
import time
from multiprocessing.dummy import Pool

import docker
from flask import _app_ctx_stack, has_app_context

from ..models import PSubmission, JudgeCaseFiles


class AppContextThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not has_app_context():
            raise RuntimeError('Running outside of Flask AppContext.')
        self.app_ctx = _app_ctx_stack.top

    def run(self):
        try:
            self.app_ctx.push()
            super().run()
        finally:
            self.app_ctx.pop()


class JudgeThreadBase(AppContextThread):
    judgers = {}

    @staticmethod
    def get_judger(task_id, lang, callback):
        return JudgeThreadBase.judgers[lang](task_id, callback)

    @staticmethod
    def convert_readable_text(text):
        lower_text = text.lower()
        if lower_text.endswith("k"):
            return int(text[:-1]) * 1024
        if lower_text.endswith("m"):
            return int(text[:-1]) * 1024 * 1024
        if lower_text.endswith("g"):
            return int(text[:-1]) * 1024 * 1024 * 1024
        return 0

    @staticmethod
    def _execute(image_name, container_name, limits, binds_list, env_list, wait_time=10):
        client = docker.DockerClient()
        service = client.services.create(
            image=image_name,
            name=container_name,
            resources=docker.types.Resources(
                mem_limit=limits['mem_limit'] * 2,
            ),
            mounts=[docker.types.Mount(
                type='bind',
                source=t[0],
                target=t[1],
            ) for t in binds_list.items()],
            env=env_list
        )
        time.sleep(wait_time)
        service.remove()
        pass

    @staticmethod
    def judge_result(correct_dir, output_dir):
        reader = Pool(10)
        reader.map()
        pass

    def get_files(self):
        task = PSubmission.query.filter_by(id=self.task_id).first()
        files = JudgeCaseFiles.query.filter_by(challenge_id=task.challenge_id).all()
        inputs = []
        outputs = []
        for i in files:
            if '.in' == i.location[-3:]:
                inputs.append(i)
            elif '.out' == i.location[-4:]:
                outputs.append(i)
        input_names = [i.location.split('/')[-1] for i in inputs]
        output_names = [i.location.split('/')[-1] for i in outputs]
        available_cases = [i[:i.rfind('.')]
                           for i in input_names
                           if i[:i.rfind('.')] + '.out' in output_names]
        j, k = 0, 0
        for i in range(len(available_cases)):
            while available_cases[i] + '.in' not in inputs[j].location:
                j += 1
            while available_cases[i] + '.out' not in outputs[k].location:
                k += 1
            yield inputs[j], outputs[k]

    def __init__(self, task_id, callback):
        super(JudgeThreadBase, self).__init__()
        self.task_id = task_id
        self.callback = callback
