


# INSERT_YOUR_CODE

# 获取脚本输入参数
IMAGE_DIR="$1"
MODEL_PATH="$2"

if [ -z "$IMAGE_DIR" ] || [ -z "$MODEL_PATH" ]; then
  echo "Usage: $0 <image_dir> <model_path>"
  exit 1
fi




# gdown https://drive.google.com/uc?id=1WEue11q9sKGe2AHTmgWH1S0ffIVHBRTR 


# echo $IMAGE_DIR
# echo $MODEL_PATH
# exit 0

python3 ../download_img_urls_from_cfd1.py --image_dir=$IMAGE_DIR


K_CENTER=2
K_REFINE=3
K_SKIP=3
MASK_MODE=res


INPUT_SIZE=256
NAME=slbr_v1
TEST_DIR=/Users/wushan/Downloads/test_imgs




CUDA_VISIBLE_DEVICES=1 python3  test_custom.py \
  --name ${NAME} \
  --nets slbr \
  --models slbr \
  --input-size ${INPUT_SIZE} \
  --crop_size ${INPUT_SIZE} \
  --test-batch 1 \
  --evaluate\
  --preprocess resize \
  --no_flip \
  --mask_mode ${MASK_MODE} \
  --k_center ${K_CENTER} \
  --use_refine \
  --k_refine ${K_REFINE} \
  --k_skip_stage ${K_SKIP} \
  --resume $MODEL_PATH \
  --test_dir ${TEST_DIR} 
  
