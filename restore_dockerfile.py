# coding: utf-8
import os
import sys
import json
import time
import subprocess
from datetime import datetime


# def exec_shell(cmd):
#     states, result = subprocess.getstatusoutput(cmd)
#     # print(states, result)
#     if states != 0:
#         print("执行命令错误!:"+cmd)
#         exit(states)
#     return result

def handle_file(cmd, target, dir, index, dockerfile_workdir):
    action = cmd.split(" ")[0]
    layer = "layer"+str(index)
    workdir = dir+"/"+layer
    subprocess.getoutput("mkdir -p "+workdir)
    add_dir = cmd.split(" ")[-1]
    if add_dir.startswith("/") == False:
        add_dir = dockerfile_workdir+"/"+add_dir
    add_dir_real = target+"/"+add_dir
    if os.path.isdir(add_dir_real):
        if add_dir == "/" and action == "ADD":
            shell = "cd " + add_dir_real+";"+"tar zcvf " + \
                workdir+"/root.tar.gz ."
            s, _ = subprocess.getstatusoutput(shell)
            if s != 0:
                print("打包错误！")
                exit(-4)
            action_cmd = action+" "+layer+"/root.tar.gz "+add_dir
        else:
            shell = "cp -r "+add_dir_real+"/* "+workdir
            s, _ = subprocess.getstatusoutput(shell)
            if s != 0:
                print("拷贝错误！")
                exit(-5)
            action_cmd = action+" "+layer+"/* "+add_dir
    elif os.path.isfile(add_dir_real):
        shell = "cp "+add_dir_real+" "+workdir
        s, _ = subprocess.getstatusoutput(shell)
        if s != 0:
            print("拷贝错误！")
            exit(-5)
        action_cmd = action+" "+layer+"/" + \
            add_dir_real.split("/")[-1]+" "+add_dir
    else:
        print(layer, "错误！")
        print(add_dir_real, "不存在！！！")
        shell = "cp -r "+target+"/* "+workdir
        s, _ = subprocess.getstatusoutput(shell)
        if s != 0:
            print("拷贝错误！")
            exit(-5)
        action_cmd = "# 此处有错误需要修改\n#"+action+" "+layer+"/* "+add_dir

    return action_cmd


def restore(image, dir):
    info = subprocess.getoutput("docker inspect "+image)
    info_j = json.loads(info)
    image_id = info_j[0]["Id"][7:]
    GraphDriverData = info_j[0]["GraphDriver"]["Data"]
    try:
        LowerDir = GraphDriverData["LowerDir"].split(":")
    except:
        LowerDir = []
    UpperDir = GraphDriverData["UpperDir"]
    dirs = [UpperDir]+LowerDir
    dirs.reverse()

    meta = subprocess.getoutput(
        "cat /var/lib/docker/image/overlay2/imagedb/content/sha256/"+image_id)
    meta_j = json.loads(meta)
    history = meta_j["history"]
    dockerfile = ["FROM scratch"]
    index = 0
    date = datetime.strptime("2000-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S")
    dockerfile_workdir = "/"
    for item in history:
        time = item["created"]
        try:
            date1 = datetime.strptime(time[0:-11], "%Y-%m-%dT%H:%M:%S")
            if (date1-date).seconds > 2*3600:
                dockerfile.append("")
                dockerfile.append("# build at "+time)
            date = date1
        except:
            pass

        cmd_raw = item["created_by"][11:]
        if cmd_raw.startswith("#(nop)"):
            cmd = cmd_raw[6:].strip()
            if cmd.startswith("WORKDIR"):
                dockerfile_workdir = cmd.split()[-1]
            if cmd.startswith("ADD") or cmd.startswith("COPY"):
                cmd = handle_file(cmd, dirs[index],
                                  dir, index, dockerfile_workdir)
                pass
            dockerfile.append(cmd)
        else:
            cmd = "RUN "+cmd_raw
            # print(cmd)
            dockerfile.append("# layer"+str(index))
            dockerfile.append(cmd)
        try:
            if item["empty_layer"] == True:
                pass
        except:
            index = index + 1

    with open(dir+"/Dockerfile", 'w') as f:
        for item in dockerfile:
            f.write(item+'\n')


def check_image(image):
    cmd = "docker inspect "+image
    s, _ = subprocess.getstatusoutput(cmd)
    if s != 0:
        return False
    return True


def check_workdir(dir):
    cmd = "ls "+dir
    s, r = subprocess.getstatusoutput(cmd)
    if s != 0:
        print("工作目录不存在！")
    if r != "":
        print("工作目录非空！")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("参数数量不正确！")
        exit(-1)
    IMAGE = sys.argv[1]
    WORKDIR = os.path.abspath(sys.argv[2])
    if check_image(IMAGE) != True:
        print("找不到镜像！")
        exit(-2)
    if check_workdir(WORKDIR) != True:
        exit(-3)
    restore(IMAGE, WORKDIR)
    print("转换完成！")
