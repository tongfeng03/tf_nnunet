# Example

To run experiments: 

```bash
CUDA_VISIBLE_DEVICES=1 \
python3 /home/fengtong/tf_nnunet/train.py \
--experiment=seg_unet3d_test \
--mode=train_and_eval \
--config_file=/home/fengtong/tf_nnunet/experiments/task_004/params_3d.yaml \
--model_dir=/mnt/SSD1/fengtong/nnunet/nnUNet_trained_models/tf_unet/task_004/3d_fold0 \
--params_override="task.train_data.input_path=[ \
/mnt/SSD1/fengtong/nnunet/nnUNet_preprocessed/Task004_Hippocampus/3d_tfrecord_data/fold1*, \
/mnt/SSD1/fengtong/nnunet/nnUNet_preprocessed/Task004_Hippocampus/3d_tfrecord_data/fold2*, \
/mnt/SSD1/fengtong/nnunet/nnUNet_preprocessed/Task004_Hippocampus/3d_tfrecord_data/fold3*, \
/mnt/SSD1/fengtong/nnunet/nnUNet_preprocessed/Task004_Hippocampus/3d_tfrecord_data/fold4*], \
task.validation_data.input_path= \
/mnt/SSD1/fengtong/nnunet/nnUNet_preprocessed/Task004_Hippocampus/3d_tfrecord_data/fold0*, \
trainer.checkpoint_interval=25000, \
trainer.validation_interval=25000, \
trainer.steps_per_loop=25000, \
trainer.summary_interval=25000, \
trainer.train_steps=250"
```
