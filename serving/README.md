# Example

To export saved model: 

```bash
CUDA_VISIBLE_DEVICES=1 \
python3 /home/fengtong/tf_nnunet/serving/export_saved_model.py \
--experiment=seg_unet3d_test \
--export_dir=/mnt/SSD1/fengtong/nnunet/nnUNet_trained_models/tf_unet/task_004/exported_model \
--checkpoint_path=/mnt/SSD1/fengtong/nnunet/nnUNet_trained_models/tf_unet/task_004/3d_fold0_tfnnunet \
--config_file=/home/fengtong/tf_nnunet/experiments/task_004/params_3d.yaml \
--batch_size=1 \
--input_image_size=40,56,40 \
--num_channels=1
```
