# Tensorflow
import tensorflow as tf

# Local
# tf.debugging.set_log_device_placement(True)
from data_augmentations.tfda_3d.augmentations.utils import (
    create_zero_centered_coordinate_mesh,
    create_zero_centered_coordinate_mesh_2D,
    elastic_deform_coordinates,
    elastic_deform_coordinates_2D,
    rotate_coords_2d,
    rotate_coords_3d,
    scale_coords,
)
from data_augmentations.tfda_3d.data_processing_utils import (
    center_crop_fn,
    interpolate_img,
    interpolate_img_2d,
    random_crop_fn,
    update_tf_channel,
)
from data_augmentations.tfda_3d.defs import TFbF, TFbT, nan, pi
from data_augmentations.tfda_3d.utils import isnotnan


def augment_spatial_helper(
    sample_id: tf.Tensor, patch_size: tf.Tensor
) -> tf.Tensor:
    pass


@tf.function(experimental_follow_type_hints=True)
def augment_spatial(
    data: tf.Tensor,
    seg: tf.Tensor,
    patch_size: tf.Tensor,
    patch_center_dist_from_border: tf.Tensor = 30,
    do_elastic_deform: tf.Tensor = TFbT,
    alpha: tf.Tensor = (0.0, 1000.0),
    sigma: tf.Tensor = (10.0, 13.0),
    do_rotation: tf.Tensor = TFbT,
    angle_x: tf.Tensor = (0, 2 * pi),
    angle_y: tf.Tensor = (0, 2 * pi),
    angle_z: tf.Tensor = (0, 2 * pi),
    do_scale: tf.Tensor = TFbT,
    scale: tf.Tensor = (0.75, 1.25),
    border_mode_data: tf.Tensor = "nearest",
    border_cval_data: tf.Tensor = 0.0,
    order_data: tf.Tensor = 3.0,
    border_mode_seg: tf.Tensor = "constant",
    border_cval_seg: tf.Tensor = 0.0,
    order_seg: tf.Tensor = 0.0,
    random_crop: tf.Tensor = TFbT,
    p_el_per_sample: tf.Tensor = 1.0,
    p_scale_per_sample: tf.Tensor = 1.0,
    p_rot_per_sample: tf.Tensor = 1.0,
    independent_scale_for_each_axis: tf.Tensor = TFbF,
    p_rot_per_axis: tf.Tensor = 1.0,
    p_independent_scale_per_axis: tf.Tensor = 1.0,
) -> tf.Tensor:
    p_el_per_sample = tf.cast(p_el_per_sample, tf.float32)
    p_scale_per_sample = tf.cast(p_scale_per_sample, tf.float32)
    p_rot_per_axis = tf.cast(p_rot_per_axis, tf.float32)
    p_rot_per_sample = tf.cast(p_rot_per_sample, tf.float32)
    p_independent_scale_per_axis = tf.cast(
        p_independent_scale_per_axis, tf.float32
    )
    # start here
    dim = tf.shape(patch_size)[0]

    # don't do it now!
    # seg_result, data_result

    # Never used
    # if not isinstance(patch_center_dist_from_border, (list, tuple, np.ndarray)):
    #     patch_center_dist_from_border = dim * [patch_center_dist_from_border]

    # for sample_id in tf.range(data.shape[0]):
    @tf.function
    def augment_per_sample(
        sample_id, patch_size, data, seg, data_result, seg_result
    ):
        patch_size = tf.cast(patch_size, tf.int64)
        coords = create_zero_centered_coordinate_mesh(patch_size)

        modified_coords = False

        coords, modified_coords = tf.cond(
            tf.logical_and(
                do_elastic_deform,
                tf.less(tf.random.uniform(()), p_el_per_sample),
            ),
            lambda: (
                elastic_deform_coordinates(
                    coords,
                    tf.random.uniform((), alpha[0], alpha[1]),
                    tf.random.uniform((), sigma[0], sigma[1]),
                ),
                True,
            ),
            lambda: (coords, modified_coords),
        )

        coords, modified_coords = tf.cond(
            tf.logical_and(
                do_rotation, tf.less(tf.random.uniform(()), p_rot_per_sample)
            ),
            lambda: (
                lambda a_x, a_y, a_z: (
                    rotate_coords_3d(coords, a_x, a_y, a_z),
                    True,
                )
            )(
                tf.cond(
                    tf.less_equal(tf.random.uniform(()), p_rot_per_axis),
                    lambda: tf.random.uniform((), angle_x[0], angle_x[1]),
                    lambda: 0.0,
                ),
                tf.cond(
                    tf.less_equal(tf.random.uniform(()), p_rot_per_axis),
                    lambda: tf.random.uniform((), angle_y[0], angle_y[1]),
                    lambda: 0.0,
                ),
                tf.cond(
                    tf.less_equal(tf.random.uniform(()), p_rot_per_axis),
                    lambda: tf.random.uniform((), angle_z[0], angle_z[1]),
                    lambda: 0.0,
                ),
            ),
            lambda: (coords, modified_coords),
        )

        coords, modified_coords = tf.cond(
            tf.logical_and(
                do_scale, tf.less(tf.random.uniform(()), p_scale_per_sample)
            ),
            lambda: (lambda sc: (scale_coords(coords, sc), True))(
                tf.cond(
                    tf.logical_and(
                        independent_scale_for_each_axis,
                        tf.less(
                            tf.random.uniform(()), p_independent_scale_per_axis
                        ),
                    ),
                    lambda: tf.map_fn(
                        lambda _x: tf.cond(
                            tf.logical_and(
                                tf.less(
                                    tf.random.uniform(()), tf.constant(0.5)
                                ),
                                tf.less(scale[0], tf.constant(1.0)),
                            ),
                            lambda: tf.random.uniform((), scale[0], 1.0),
                            lambda: tf.random.uniform(
                                (), tf.maximum(scale[0], 1.0), scale[1]
                            ),
                        ),
                        tf.range(dim, dtype=tf.float32),
                    ),
                    lambda: tf.cond(
                        tf.logical_and(
                            tf.less(tf.random.uniform(()), 0.5),
                            tf.less(scale[0], 1.0),
                        ),
                        lambda: tf.random.uniform((), scale[0], 1.0),
                        lambda: tf.random.uniform(
                            (), tf.maximum(scale[0], 1.0), scale[1]
                        ),
                    ),
                )
            ),
            lambda: (coords, modified_coords),
        )

        # add from here
        if modified_coords:

            d = tf.constant(0, dtype=tf.int64)
            loop_cond = lambda d, coords: tf.less(d, dim)

            @tf.function
            def body_fn(d, coords):
                # random crop always false
                # if random_crop:
                #     ctr = tf.random.uniform(
                #         [],
                #         patch_center_dist_from_border[d],
                #         tf.cast(tf.shape(data)[d + 2], dtype=tf.float32)
                #         - patch_center_dist_from_border[d],
                #     )
                # else:
                #     ctr = (
                #         tf.cast(tf.shape(data)[d + 2], dtype=tf.float32) / 2.0
                #         - 0.5
                #     )
                ctr = (
                    tf.cast(tf.shape(data)[d + 2], dtype=tf.float32) / 2.0
                    - 0.5
                )
                coords_d = coords[d] + ctr
                coords = update_tf_channel(coords, d, coords_d)
                d = d + 1
                # coords.set_shape([3, None, None, None])
                return d, coords

            _, coords = tf.while_loop(
                loop_cond,
                body_fn,
                [d, coords],
                shape_invariants=[tf.TensorShape(None), coords.get_shape()],
            )
            data_sample = tf.zeros(tf.shape(data_result)[1:])
            channel_id = tf.constant(0)
            cond_to_loop_data = lambda channel_id, _data_sample: tf.less(
                channel_id, tf.shape(data)[1]
            )

            @tf.function
            def body_fn_data(channel_id, data_sample):
                data_channel = interpolate_img(
                    data[sample_id, channel_id],
                    coords,
                    order_data,
                    border_mode_data,
                    border_cval_data,
                )
                data_sample = update_tf_channel(
                    data_sample, channel_id, data_channel
                )
                channel_id = channel_id + 1
                return channel_id, data_sample

            _, data_sample = tf.while_loop(
                cond_to_loop_data, body_fn_data, [channel_id, data_sample]
            )
            data_result = update_tf_channel(
                data_result, sample_id, data_sample
            )
            # TODO
            # if isnotnan(seg):
            if True:
                seg_sample = tf.zeros(tf.shape(seg_result)[1:])
                channel_id = tf.constant(0)
                cond_to_loop_seg = lambda channel_id, seg_sample: tf.less(
                    channel_id, tf.shape(seg)[1]
                )

                @tf.function
                def body_fn_seg(channel_id, seg_sample):
                    seg_channel = interpolate_img(
                        seg[sample_id, channel_id],
                        coords,
                        order_seg,
                        border_mode_seg,
                        border_cval_seg,
                        is_seg=TFbT,
                    )
                    seg_sample = update_tf_channel(
                        seg_sample, channel_id, seg_channel
                    )
                    channel_id = channel_id + 1
                    return channel_id, seg_sample

                _, seg_sample = tf.while_loop(
                    cond_to_loop_seg, body_fn_seg, [channel_id, seg_sample]
                )
                seg_result = update_tf_channel(
                    seg_result, sample_id, seg_sample
                )
        else:
            # TODO
            # s = nan
            # if tf.math.reduce_any(tf.math.is_nan(seg)):
            #     s = nan
            # else:
            #     s = seg[sample_id : sample_id + 1]

            s = seg[sample_id : sample_id + 1]

            # if random_crop:
            #     # margin = [patch_center_dist_from_border[d] - tf.cast(patch_size[d], dtype=tf.float32) // 2 for d in tf.range(dim)]
            #     margin = tf.map_fn(
            #         lambda d: tf.cast(
            #             patch_center_dist_from_border[d], dtype=tf.int64
            #         )
            #         - patch_size[d] // 2,
            #         elems=tf.range(dim),
            #     )
            #     d, s = random_crop_fn(
            #         data[sample_id : sample_id + 1], s, patch_size, margin
            #     )
            # else:
            #     d, s = center_crop_fn(
            #         data[sample_id : sample_id + 1], patch_size, s
            #     )
            d, s = center_crop_fn(
                data[sample_id : sample_id + 1], patch_size, s
            )
            data_result = update_tf_channel(data_result, sample_id, d[0])

            # TODO
            # if isnotnan(seg):
            if True:
                seg_result = update_tf_channel(seg_result, sample_id, s[0])
        sample_id = sample_id + 1
        return sample_id, patch_size, data, seg, data_result, seg_result

    # spatial augment main body
    patch_size = tf.convert_to_tensor(patch_size)

    patch_center_dist_from_border = tf.cast(
        patch_center_dist_from_border, dtype=tf.float32
    )
    patch_size = tf.cast(patch_size, tf.int64)
    cond_to_loop = lambda sample_id, patch_size, data, seg, data_result, seg_result: tf.less(
        sample_id, sample_num
    )
    dim = tf.cast(tf.shape(patch_size)[0], tf.int64)
    seg_result = nan

    # TODO
    # if isnotnan(seg):
    if True:
        seg_result = tf.zeros(
            tf.concat(
                [tf.shape(seg, out_type=tf.int64)[:2], patch_size[:3]],
                axis=0,
            )
        )

    data_result = tf.zeros(
        tf.concat(
            [tf.shape(data, out_type=tf.int64)[:2], patch_size[:3]], axis=0
        )
    )
    sample_num = tf.shape(data)[0]
    sample_id = tf.constant(0)
    _, _, _, _, data_result, seg_result = tf.while_loop(
        cond_to_loop,
        augment_per_sample,
        [sample_id, patch_size, data, seg, data_result, seg_result],
    )
    return data_result, seg_result


@tf.function(experimental_follow_type_hints=True)
def augment_spatial_2D(
    data: tf.Tensor,
    seg: tf.Tensor,
    patch_size: tf.Tensor,
    patch_center_dist_from_border: tf.Tensor = 30,
    do_elastic_deform: tf.Tensor = TFbT,
    alpha: tf.Tensor = (0.0, 1000.0),
    sigma: tf.Tensor = (10.0, 13.0),
    do_rotation: tf.Tensor = TFbT,
    angle_x: tf.Tensor = (0, 2 * pi),
    angle_y: tf.Tensor = (0, 2 * pi),
    angle_z: tf.Tensor = (0, 2 * pi),
    do_scale: tf.Tensor = TFbT,
    scale: tf.Tensor = (0.75, 1.25),
    border_mode_data: tf.Tensor = "nearest",
    border_cval_data: tf.Tensor = 0.0,
    order_data: tf.Tensor = 3.0,
    border_mode_seg: tf.Tensor = "constant",
    border_cval_seg: tf.Tensor = 0.0,
    order_seg: tf.Tensor = 0.0,
    random_crop: tf.Tensor = TFbT,
    p_el_per_sample: tf.Tensor = 1.0,
    p_scale_per_sample: tf.Tensor = 1.0,
    p_rot_per_sample: tf.Tensor = 1.0,
    independent_scale_for_each_axis: tf.Tensor = TFbF,
    p_rot_per_axis: tf.Tensor = 1.0,
    p_independent_scale_per_axis: tf.Tensor = 1.0,
) -> tf.Tensor:
    p_el_per_sample = tf.cast(p_el_per_sample, tf.float32)
    p_scale_per_sample = tf.cast(p_scale_per_sample, tf.float32)
    p_rot_per_axis = tf.cast(p_rot_per_axis, tf.float32)
    p_rot_per_sample = tf.cast(p_rot_per_sample, tf.float32)
    p_independent_scale_per_axis = tf.cast(
        p_independent_scale_per_axis, tf.float32
    )
    # start here
    dim = tf.shape(patch_size)[0]

    @tf.function
    def augment_per_sample(
        sample_id, patch_size, data, seg, data_result, seg_result
    ):
        # tf.print(sample_id)
        patch_size = tf.cast(patch_size, tf.int64)
        # tf.print('111')
        coords = create_zero_centered_coordinate_mesh_2D(patch_size)

        modified_coords = False

        # tf.print('222')
        coords, modified_coords = tf.cond(
            tf.logical_and(
                do_elastic_deform,
                tf.less(tf.random.uniform(()), p_el_per_sample),
            ),
            lambda: (
                elastic_deform_coordinates_2D(
                    coords,
                    tf.random.uniform((), alpha[0], alpha[1]),
                    tf.random.uniform((), sigma[0], sigma[1]),
                ),
                True,
            ),
            lambda: (coords, modified_coords),
        )

        # tf.print('333')
        coords, modified_coords = tf.cond(
            tf.logical_and(
                do_rotation, tf.less(tf.random.uniform(()), p_rot_per_sample)
            ),
            lambda: (lambda a_x: (rotate_coords_2d(coords, a_x), True,))(
                tf.cond(
                    tf.less_equal(tf.random.uniform(()), p_rot_per_axis),
                    lambda: tf.random.uniform((), angle_x[0], angle_x[1]),
                    lambda: 0.0,
                )
            ),
            lambda: (coords, modified_coords),
        )

        # tf.print('444')
        coords, modified_coords = tf.cond(
            tf.logical_and(
                do_scale, tf.less(tf.random.uniform(()), p_scale_per_sample)
            ),
            lambda: (lambda sc: (scale_coords(coords, sc), True))(
                tf.cond(
                    tf.logical_and(
                        independent_scale_for_each_axis,
                        tf.less(
                            tf.random.uniform(()), p_independent_scale_per_axis
                        ),
                    ),
                    lambda: tf.map_fn(
                        lambda _x: tf.cond(
                            tf.logical_and(
                                tf.less(
                                    tf.random.uniform(()), tf.constant(0.5)
                                ),
                                tf.less(scale[0], tf.constant(1.0)),
                            ),
                            lambda: tf.random.uniform((), scale[0], 1.0),
                            lambda: tf.random.uniform(
                                (), tf.maximum(scale[0], 1.0), scale[1]
                            ),
                        ),
                        tf.range(dim, dtype=tf.float32),
                    ),
                    lambda: tf.cond(
                        tf.logical_and(
                            tf.less(tf.random.uniform(()), 0.5),
                            tf.less(scale[0], 1.0),
                        ),
                        lambda: tf.random.uniform((), scale[0], 1.0),
                        lambda: tf.random.uniform(
                            (), tf.maximum(scale[0], 1.0), scale[1]
                        ),
                    ),
                )
            ),
            lambda: (coords, modified_coords),
        )

        # tf.print('555')
        # add from here
        if modified_coords:

            d = tf.constant(0, dtype=tf.int64)
            loop_cond = lambda d, coords: tf.less(d, dim)

            @tf.function
            def body_fn(d, coords):
                # random crop always false
                # if random_crop:
                #     ctr = tf.random.uniform(
                #         [],
                #         patch_center_dist_from_border[d],
                #         tf.cast(tf.shape(data)[d + 2], dtype=tf.float32)
                #         - patch_center_dist_from_border[d],
                #     )
                # else:
                #     ctr = (
                #         tf.cast(tf.shape(data)[d + 2], dtype=tf.float32) / 2.0
                #         - 0.5
                #     )
                ctr = (
                    tf.cast(tf.shape(data)[d + 2], dtype=tf.float32) / 2.0
                    - 0.5
                )
                coords_d = coords[d] + ctr
                coords = update_tf_channel(coords, d, coords_d)
                d = d + 1
                # coords.set_shape([3, None, None, None])
                return d, coords

            _, coords = tf.while_loop(
                loop_cond,
                body_fn,
                [d, coords],
                shape_invariants=[tf.TensorShape(None), coords.get_shape()],
            )
            data_sample = tf.zeros(tf.shape(data_result)[1:])
            channel_id = tf.constant(0)
            cond_to_loop_data = lambda channel_id, _data_sample: tf.less(
                channel_id, tf.shape(data)[1]
            )

            @tf.function
            def body_fn_data(channel_id, data_sample):
                data_channel = interpolate_img_2d(
                    data[sample_id, channel_id],
                    coords,
                    order_data,
                    border_mode_data,
                    border_cval_data,
                )
                data_sample = update_tf_channel(
                    data_sample, channel_id, data_channel
                )
                channel_id = channel_id + 1
                return channel_id, data_sample

            _, data_sample = tf.while_loop(
                cond_to_loop_data, body_fn_data, [channel_id, data_sample]
            )
            data_result = update_tf_channel(
                data_result, sample_id, data_sample
            )
            # TODO
            # if isnotnan(seg):
            if True:
                seg_sample = tf.zeros(tf.shape(seg_result)[1:])
                channel_id = tf.constant(0)
                cond_to_loop_seg = lambda channel_id, seg_sample: tf.less(
                    channel_id, tf.shape(seg)[1]
                )

                @tf.function
                def body_fn_seg(channel_id, seg_sample):
                    seg_channel = interpolate_img_2d(
                        seg[sample_id, channel_id],
                        coords,
                        order_seg,
                        border_mode_seg,
                        border_cval_seg,
                        is_seg=TFbT,
                    )
                    seg_sample = update_tf_channel(
                        seg_sample, channel_id, seg_channel
                    )
                    channel_id = channel_id + 1
                    return channel_id, seg_sample

                _, seg_sample = tf.while_loop(
                    cond_to_loop_seg, body_fn_seg, [channel_id, seg_sample]
                )
                seg_result = update_tf_channel(
                    seg_result, sample_id, seg_sample
                )
        else:
            # TODO
            # s = nan
            # if tf.math.reduce_any(tf.math.is_nan(seg)):
            #     s = nan
            # else:
            #     s = seg[sample_id : sample_id + 1]

            s = seg[sample_id : sample_id + 1]

            # if random_crop:
            #     # margin = [patch_center_dist_from_border[d] - tf.cast(patch_size[d], dtype=tf.float32) // 2 for d in tf.range(dim)]
            #     margin = tf.map_fn(
            #         lambda d: tf.cast(
            #             patch_center_dist_from_border[d], dtype=tf.int64
            #         )
            #         - patch_size[d] // 2,
            #         elems=tf.range(dim),
            #     )
            #     d, s = random_crop_fn(
            #         data[sample_id : sample_id + 1], s, patch_size, margin
            #     )
            # else:
            #     d, s = center_crop_fn(
            #         data[sample_id : sample_id + 1], patch_size, s
            #     )
            d, s = center_crop_fn(
                data[sample_id : sample_id + 1], patch_size, s
            )
            data_result = update_tf_channel(data_result, sample_id, d[0])

            # TODO
            # if isnotnan(seg):
            if True:
                seg_result = update_tf_channel(seg_result, sample_id, s[0])
        sample_id = sample_id + 1
        # tf.print('666')
        return sample_id, patch_size, data, seg, data_result, seg_result

    # spatial augment main body
    patch_size = tf.convert_to_tensor(patch_size)

    patch_center_dist_from_border = tf.cast(
        patch_center_dist_from_border, dtype=tf.float32
    )
    patch_size = tf.cast(patch_size, tf.int64)
    cond_to_loop = lambda sample_id, patch_size, data, seg, data_result, seg_result: tf.less(
        sample_id, sample_num
    )
    dim = tf.cast(tf.shape(patch_size)[0], tf.int64)
    seg_result = nan

    # TODO
    # if isnotnan(seg):
    if True:
        seg_result = tf.zeros(
            tf.concat(
                [tf.shape(seg, out_type=tf.int64)[:2], patch_size[:2]],
                axis=0,
            )
        )
    data_result = tf.zeros(
        tf.concat(
            [tf.shape(data, out_type=tf.int64)[:2], patch_size[:2]], axis=0
        )
    )
    sample_num = tf.shape(data)[0]
    sample_id = tf.constant(0)
    _, _, _, _, data_result, seg_result = tf.while_loop(
        cond_to_loop,
        augment_per_sample,
        [sample_id, patch_size, data, seg, data_result, seg_result],
    )
    return data_result, seg_result


@tf.function(experimental_follow_type_hints=True)
def augment_mirroring(
    sample_data: tf.Tensor,
    sample_seg: tf.Tensor = nan,
    axes: tf.Tensor = (0, 1, 2),
) -> tf.Tensor:
    # if (tf.rank(sample_data) != 3) and (tf.rank(sample_data) != 4):
    #     tf.get_logger().warn(
    #         "Invalid dimension for sample_data and sample_seg. sample_data and sample_seg should be either "
    #         "[channels, x, y] or [channels, x, y, z]\n"
    #         "return raw")
    #     return sample_data, sample_seg
    sample_data, sample_seg = tf.cond(
        tf.logical_and(
            tf.reduce_any(tf.equal(axes, 0)),
            tf.less(tf.random.uniform(()), 0.5),
        ),
        lambda: (
            sample_data[:, ::-1],
            tf.cond(
                isnotnan(sample_seg),
                lambda: sample_seg[:, ::-1],
                lambda: sample_seg,
            ),
        ),
        lambda: (sample_data, sample_seg),
    )

    sample_data, sample_seg = tf.cond(
        tf.logical_and(
            tf.reduce_any(tf.equal(axes, 1)),
            tf.less(tf.random.uniform(()), 0.5),
        ),
        lambda: (
            sample_data[:, :, ::-1],
            tf.cond(
                isnotnan(sample_seg),
                lambda: sample_seg[:, :, ::-1],
                lambda: sample_seg,
            ),
        ),
        lambda: (sample_data, sample_seg),
    )

    sample_data, sample_seg = tf.cond(
        tf.logical_and(
            tf.reduce_any(tf.equal(axes, 2)),
            tf.less(tf.random.uniform(()), 0.5),
        ),
        lambda: (
            sample_data[:, :, ::-1],
            tf.cond(
                isnotnan(sample_seg),
                lambda: sample_seg[:, :, ::-1],
                lambda: sample_seg,
            ),
        ),
        lambda: (sample_data, sample_seg),
    )

    return sample_data, sample_seg


@tf.function(experimental_follow_type_hints=True)
def augment_mirroring_2D(
    sample_data: tf.Tensor,
    sample_seg: tf.Tensor = nan,
    axes: tf.Tensor = (0, 1),
) -> tf.Tensor:
    # if (tf.rank(sample_data) != 3) and (tf.rank(sample_data) != 4):
    #     tf.get_logger().warn(
    #         "Invalid dimension for sample_data and sample_seg. sample_data and sample_seg should be either "
    #         "[channels, x, y] or [channels, x, y, z]\n"
    #         "return raw")
    #     return sample_data, sample_seg
    sample_data, sample_seg = tf.cond(
        tf.logical_and(
            tf.reduce_any(tf.equal(axes, 0)),
            tf.less(tf.random.uniform(()), 0.5),
        ),
        lambda: (
            sample_data[:, ::-1],
            tf.cond(
                isnotnan(sample_seg),
                lambda: sample_seg[:, ::-1],
                lambda: sample_seg,
            ),
        ),
        lambda: (sample_data, sample_seg),
    )

    sample_data, sample_seg = tf.cond(
        tf.logical_and(
            tf.reduce_any(tf.equal(axes, 1)),
            tf.less(tf.random.uniform(()), 0.5),
        ),
        lambda: (
            sample_data[:, :, ::-1],
            tf.cond(
                isnotnan(sample_seg),
                lambda: sample_seg[:, :, ::-1],
                lambda: sample_seg,
            ),
        ),
        lambda: (sample_data, sample_seg),
    )

    return sample_data, sample_seg


if __name__ == "__main__":
    data = tf.ones([1, 40, 36, 36])
    seg = tf.ones([1, 40, 36, 36])
    patch_size = tf.cast([20, 20], tf.int64)
    # mirrored_strategy = tf.distribute.MirroredStrategy()

    with tf.device("/CPU:0"):
        # with mirrored_strategy.scope():
        tf.config.run_functions_eagerly(True)
        data, seg = augment_spatial_2D(data, seg, patch_size, random_crop=TFbF)
        tf.print(tf.shape(data), tf.shape(seg))
        tf.config.run_functions_eagerly(False)
        # augment_spatial(data, seg, patch_size)
        # augment_spatial(data, seg, patch_size)
