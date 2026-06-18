#!/usr/bin/env bash

set -e

TARGET_MODEL=${1:-}


if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-tiny"*. ]]; then
    # yolov3-tiny
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov3-tiny.cfg -q --show-progress --no-clobber
    wget https://pjreddie.com/media/files/yolov3-tiny.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-"[0-9]+. ]]; then
    # yolov3
    wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg -q --show-progress --no-clobber
    wget https://pjreddie.com/media/files/yolov3.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-spp"*. ]]; then
    # yolov3-spp
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov3-spp.cfg -q --show-progress --no-clobber
    wget https://pjreddie.com/media/files/yolov3-spp.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || { [[ $TARGET_MODEL =~ .*"yolov4-tiny"*. ]] && ! [[ $TARGET_MODEL =~ .*"_gun"*. ]]; }; then
    # yolov4-tiny
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg -q --show-progress --no-clobber
    wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4-tiny.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-"[0-9]+. ]]; then
    # yolov4
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4.cfg -q --show-progress --no-clobber
    wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v3_optimal/yolov4.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-csp"*. ]]; then
    # yolov4-csp
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-csp.cfg -q --show-progress --no-clobber
    wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4-csp.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4x-mish"*. ]]; then
    # yolov4x-mish
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4x-mish.cfg -q --show-progress --no-clobber
    wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4x-mish.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-p5"*. ]]; then
    # yolov4-p5
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-p5.cfg -q --show-progress --no-clobber
    wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4-p5.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7-tiny"*. ]]; then
    # yolov7-tiny
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov7-tiny.cfg -q --show-progress --no-clobber
    wget https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov7-tiny.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7-"[0-9]+. ]]; then
    # yolov7
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov7.cfg -q --show-progress --no-clobber
    wget https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov7.weights -q --show-progress --no-clobber
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7x-"*. ]]; then
    # yolov7x
    wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov7x.cfg -q --show-progress --no-clobber
    wget https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov7x.weights -q --show-progress --no-clobber
fi


echo

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-tiny-288"*. ]]; then
    echo "Creating yolov3-tiny-288.cfg and yolov3-tiny-288.weights"
    cat yolov3-tiny.cfg | sed -e '8s/width=416/width=288/' | sed -e '9s/height=416/height=288/' > yolov3-tiny-288.cfg
    echo >> yolov3-tiny-288.cfg
    ln -sf yolov3-tiny.weights yolov3-tiny-288.weights
fi
if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-tiny-416"*. ]]; then
    echo "Creating yolov3-tiny-416.cfg and yolov3-tiny-416.weights"
    cp yolov3-tiny.cfg yolov3-tiny-416.cfg
    echo >> yolov3-tiny-416.cfg
    ln -sf yolov3-tiny.weights yolov3-tiny-416.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-288"*. ]]; then
    echo "Creating yolov3-288.cfg and yolov3-288.weights"
    cat yolov3.cfg | sed -e '8s/width=608/width=288/' | sed -e '9s/height=608/height=288/' > yolov3-288.cfg
    ln -sf yolov3.weights yolov3-288.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-416"*. ]]; then
    echo "Creating yolov3-416.cfg and yolov3-416.weights"
    cat yolov3.cfg | sed -e '8s/width=608/width=416/' | sed -e '9s/height=608/height=416/' > yolov3-416.cfg
    ln -sf yolov3.weights yolov3-416.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-608"*. ]]; then
    echo "Creating yolov3-608.cfg and yolov3-608.weights"
    cp yolov3.cfg yolov3-608.cfg
    ln -sf yolov3.weights yolov3-608.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-spp-288"*. ]]; then
    echo "Creating yolov3-spp-288.cfg and yolov3-spp-288.weights"
    cat yolov3-spp.cfg | sed -e '8s/width=608/width=288/' | sed -e '9s/height=608/height=288/' > yolov3-spp-288.cfg
    ln -sf yolov3-spp.weights yolov3-spp-288.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-spp-416"*. ]]; then
    echo "Creating yolov3-spp-416.cfg and yolov3-spp-416.weights"
    cat yolov3-spp.cfg | sed -e '8s/width=608/width=416/' | sed -e '9s/height=608/height=416/' > yolov3-spp-416.cfg
    ln -sf yolov3-spp.weights yolov3-spp-416.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov3-spp-608"*. ]]; then
    echo "Creating yolov3-spp-608.cfg and yolov3-spp-608.weights"
    cp yolov3-spp.cfg yolov3-spp-608.cfg
    ln -sf yolov3-spp.weights yolov3-spp-608.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-tiny-288_gun_v3"*. ]]; then
    echo "clean and create yolov4-tiny-288_gun_v3"
    rm -f yolov4-tiny-288_gun_v3.cfg yolov4-tiny-288_gun_v3.weights
    # yolov4-tiny-288_gun_v3
    wget https://sensecraft-statics.oss-us-east-1.aliyuncs.com/edge-ai/models/yolov4/yolov4-tiny-288_gun.cfg -q --show-progress --no-clobber -O yolov4-tiny-288_gun_v3.cfg
    echo "Got cfg of yolov4-tiny-288_gun_v3"
    wget https://sensecraft-statics.oss-us-east-1.aliyuncs.com/edge-ai/models/yolov4/yolov4-tiny-288_best_v3.weights -q --show-progress --no-clobber -O yolov4-tiny-288_gun_v3.weights
    echo "Got weights of yolov4-tiny-288_gun_v3"
fi

if [[ -z "$TARGET_MODEL" ]] || { [[ $TARGET_MODEL =~ .*"yolov4-tiny-288"*. ]] && ! [[ $TARGET_MODEL =~ .*"_gun"*. ]]; }; then
    echo "Creating yolov4-tiny-288.cfg and yolov4-tiny-288.weights"
    cat yolov4-tiny.cfg | sed -e '6s/batch=64/batch=1/' | sed -e '8s/width=416/width=288/' | sed -e '9s/height=416/height=288/' > yolov4-tiny-288.cfg
    echo >> yolov4-tiny-288.cfg
    ln -sf yolov4-tiny.weights yolov4-tiny-288.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-tiny-416"*. ]]; then
    echo "Creating yolov4-tiny-416.cfg and yolov4-tiny-416.weights"
    cat yolov4-tiny.cfg | sed -e '6s/batch=64/batch=1/' > yolov4-tiny-416.cfg
    echo >> yolov4-tiny-416.cfg
    ln -sf yolov4-tiny.weights yolov4-tiny-416.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-288"*. ]]; then
    echo "Creating yolov4-288.cfg and yolov4-288.weights"
    cat yolov4.cfg | sed -e '2s/batch=64/batch=1/' | sed -e '7s/width=608/width=288/' | sed -e '8s/height=608/height=288/' > yolov4-288.cfg
    ln -sf yolov4.weights yolov4-288.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-416"*. ]]; then
    echo "Creating yolov4-416.cfg and yolov4-416.weights"
    cat yolov4.cfg | sed -e '2s/batch=64/batch=1/' | sed -e '7s/width=608/width=416/' | sed -e '8s/height=608/height=416/' > yolov4-416.cfg
    ln -sf yolov4.weights yolov4-416.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-608"*. ]]; then
    echo "Creating yolov4-608.cfg and yolov4-608.weights"
    cat yolov4.cfg | sed -e '2s/batch=64/batch=1/' > yolov4-608.cfg
    ln -sf yolov4.weights yolov4-608.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-csp-256"*. ]]; then
    echo "Creating yolov4-csp-256.cfg and yolov4-csp-256.weights"
    cat yolov4-csp.cfg | sed -e '6s/batch=64/batch=1/' | sed -e '8s/width=512/width=256/' | sed -e '9s/height=512/height=256/' > yolov4-csp-256.cfg
    ln -sf yolov4-csp.weights yolov4-csp-256.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-csp-512"*. ]]; then
    echo "Creating yolov4-csp-512.cfg and yolov4-csp-512.weights"
    cat yolov4-csp.cfg | sed -e '6s/batch=64/batch=1/' > yolov4-csp-512.cfg
    ln -sf yolov4-csp.weights yolov4-csp-512.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4x-mish-320"*. ]]; then
    echo "Creating yolov4x-mish-320.cfg and yolov4x-mish-320.weights"
    cat yolov4x-mish.cfg | sed -e '6s/batch=64/batch=1/' | sed -e '8s/width=640/width=320/' | sed -e '9s/height=640/height=320/' > yolov4x-mish-320.cfg
    ln -sf yolov4x-mish.weights yolov4x-mish-320.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4x-mish-640"*. ]]; then
    echo "Creating yolov4x-mish-640.cfg and yolov4x-mish-640.weights"
    cat yolov4x-mish.cfg | sed -e '6s/batch=64/batch=1/' > yolov4x-mish-640.cfg
    ln -sf yolov4x-mish.weights yolov4x-mish-640.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-p5-448"*. ]]; then
    echo "Creating yolov4-p5-448.cfg and yolov4-p5-448.weights"
    cat yolov4-p5.cfg | sed -e '6s/batch=64/batch=1/' | sed -e '8s/width=896/width=448/' | sed -e '9s/height=896/height=448/' > yolov4-p5-448.cfg
    ln -sf yolov4-p5.weights yolov4-p5-448.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov4-p5-896"*. ]]; then
    echo "Creating yolov4-p5-896.cfg and yolov4-p5-896.weights"
    cat yolov4-p5.cfg | sed -e '6s/batch=64/batch=1/' > yolov4-p5-896.cfg
    ln -sf yolov4-p5.weights yolov4-p5-896.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7-tiny-288"*. ]]; then
    echo "Creating yolov7-tiny-288.cfg and yolov7-tiny-288.weights"
    cat yolov7-tiny.cfg | sed -e '6s/batch=64/batch=1/' | sed -e '8s/width=416/width=288/' | sed -e '9s/height=416/height=288/' > yolov7-tiny-288.cfg
    echo >> yolov7-tiny-288.cfg
    ln -sf yolov7-tiny.weights yolov7-tiny-288.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7-tiny-416"*. ]]; then
    echo "Creating yolov7-tiny-416.cfg and yolov7-tiny-416.weights"
    cat yolov7-tiny.cfg | sed -e '6s/batch=64/batch=1/' > yolov7-tiny-416.cfg
    echo >> yolov7-tiny-416.cfg
    ln -sf yolov7-tiny.weights yolov7-tiny-416.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7-320"*. ]]; then
    echo "Creating yolov7-320.cfg and yolov7-320.weights"
    cat yolov7.cfg | sed -e '6s/batch=64/batch=1/' | sed -e '8s/width=640/width=320/' | sed -e '9s/height=640/height=320/' > yolov7-320.cfg
    ln -sf yolov7.weights yolov7-320.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7-416"*. ]]; then
    echo "Creating yolov7-416.cfg and yolov7-416.weights"
    cat yolov7.cfg | sed -e '6s/batch=64/batch=1/' | sed -e '8s/width=640/width=416/' | sed -e '9s/height=640/height=416/' > yolov7-416.cfg
    ln -sf yolov7.weights yolov7-416.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7-640"*. ]]; then
    echo "Creating yolov7-640.cfg and yolov7-640.weights"
    cat yolov7.cfg | sed -e '6s/batch=64/batch=1/' > yolov7-640.cfg
    ln -sf yolov7.weights yolov7-640.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7x-320"*. ]]; then
    echo "Creating yolov7x-320.cfg and yolov7x-320.weights"
    cat yolov7x.cfg | sed -e '6s/batch=64/batch=1/' | sed -e '8s/width=640/width=320/' | sed -e '9s/height=640/height=320/' > yolov7x-320.cfg
    ln -sf yolov7x.weights yolov7x-320.weights
fi

if [[ -z "$TARGET_MODEL" ]] || [[ $TARGET_MODEL =~ .*"yolov7x-640"*. ]]; then
    echo "Creating yolov7x-640.cfg and yolov7x-640.weights"
    cat yolov7x.cfg | sed -e '6s/batch=64/batch=1/' > yolov7x-640.cfg
    ln -sf yolov7x.weights yolov7x-640.weights
fi

echo
echo "Done."
