import numpy as np
import os
import momentnet
import random
import tensorflow as tf
import json
import dataformat
import shutil

weight_set_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "weight_sets")
weight_sets = []


def discover_weight_set():
    weight_sets.clear()
    for name in os.listdir(weight_set_path):
        pwd = os.path.join(weight_set_path, name)
        set_file = os.path.join(pwd, "set.json")
        if os.path.isdir(pwd) and os.path.exists(set_file):
            with open(set_file, "r") as file:
                set_data = json.load(file)
                weight_sets.append(set_data)


discover_weight_set()


template_set_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")
template_paths = []


def discover_template_set():
    template_paths.clear()
    for name in os.listdir(template_set_path):
        pwd = os.path.join(template_set_path, name)
        if os.path.isdir(pwd):
            template_paths.append(name)


discover_template_set()


class Runner:

    def __init__(self):
        self.running = False
        self.setup(0)
        self.change_template(0)
        self.collect_template_flag = -1

    def change_template(self, template_index):
        if len(template_paths) < template_index:
            return False
        self.template_index = template_index
        self.templates, self.template_labels = dataformat.read_template_directory(self.formatter, os.path.join(template_set_path, template_paths[self.template_index]), with_flip=True)
        print(template_paths[self.template_index])
        return True

    def setup(self, index):
        self.index = index
        if len(weight_sets) <= self.index:
            return False
        s = weight_sets[self.index]["size"]
        self.size = (s[0], s[1])
        self.num_layers = weight_sets[self.index]["num_layers"]
        self.session_name = "weight_sets/" + weight_sets[self.index]["session_name"]

        self.formatter = dataformat.DataFormat(self.size[0])

        self.close_down()

        print(self.session_name)
        num_intra_class = 10
        num_inter_class = 20
        self.comparator = momentnet.Comparator((2, self.size[0]), self.size[1], num_intra_class=num_intra_class, num_inter_class=num_inter_class, layers=self.num_layers)

        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        self.running = True
        self.sess = tf.Session(config=config)
        self.sess.run(tf.global_variables_initializer())
        self.comparator.load_session(self.sess, self.session_name)
        return True

    def process(self, frames):
        if not self.running:
            return None

        if isinstance(frames, list):
            data = np.zeros([len(frames), 2, self.size[0]], dtype=np.float32)
            for i, frame in enumerate(frames):
                data[i, ...] = self.formatter.format(frame)
            c, raw = self.comparator.process(self.sess, np.reshape(data, [-1, self.size[0] * 2]), np.reshape(self.templates, [-1, self.size[0] * 2]))
            raw = raw[:, c].flatten()
            classes = self.template_labels[c, 0]
            flip_or_not = self.template_labels[c, 1]

        else:
            frame = frames
            data = self.formatter.format(frame)
            c, raw = self.comparator.process(self.sess, np.reshape(data, [-1, self.size[0] * 2]), np.reshape(self.templates, [-1, self.size[0] * 2]))
            raw = raw[:, c].flatten()
            classes = self.template_labels[c, 0]
            flip_or_not = self.template_labels[c, 1]
            if self.collect_template_flag >= 0:
                print(self.collect_template_flag)
                dataformat.write_to_template_directory(frame, random.randint(0, 100000), self.collect_template_flag, self.formatter, template_paths[self.template_index])
                self.collect_template_flag = -1

        return classes, raw, flip_or_not

    def raise_template_flag(self, label):
        print(label)
        self.collect_template_flag = int(label)

    def close_down(self):
        if self.running:
            self.sess.close()
            tf.reset_default_graph()
        self.running = False

    def get_weight_sets(self):
        discover_weight_set()
        return weight_sets, self.index

    def get_template_sets(self):
        discover_template_set()
        return template_paths, self.template_index

    def archive_selected(self):
        artifact_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "artifacts")
        pack_dir = os.path.join(artifact_dir, "pack")
        if os.path.exists(pack_dir):
            shutil.rmtree(os.path.join(artifact_dir, "pack"))
        os.makedirs(os.path.join(artifact_dir, "pack"))
        weight_path = "/".join(weight_sets[self.index]["session_name"].split("/")[:-1])
        print(weight_path)
        shutil.copytree(os.path.join(weight_set_path, weight_path), os.path.join(artifact_dir, "pack", weight_path))
        shutil.copytree(os.path.join(template_set_path, template_paths[self.template_index]), os.path.join(artifact_dir, "pack", "templates"))
        shutil.make_archive(os.path.join(artifact_dir, "pack"), 'gztar', os.path.join(artifact_dir, "pack"))
        return os.path.join(artifact_dir, "pack.tar.gz")


if __name__ == '__main__':

    for weight in weight_sets:
        print(weight)

    for path in template_paths:
        print(path)
