import tensorflow as tf
x = tf.constant([[0.1, 0.5], [0.3, 0.9]])
out = tf.raw_ops.QuantizeAndDequantizeV2(input=x, input_min=tf.constant([0.0, 0.0]), input_max=tf.constant([1.0, 1.0]),
                                         range_given=True, axis=-1)
print(out)
