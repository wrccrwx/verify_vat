# !/usr/bin/env python
# -*- coding:utf-8 -*-

from __future__ import print_function
import keras
from keras import backend as K
from keras.datasets import cifar10
from keras.preprocessing.image import ImageDataGenerator
from keras.engine.topology import Input, Container
from keras.engine.training import Model
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten, advanced_activations, BatchNormalization
from keras.layers import Conv2D, MaxPooling2D, Convolution2D, pooling
import os

import numpy as np

from functools import reduce

batch_size = 100
num_classes = 10
epochs = 300
num_predictions = 20
save_dir = os.path.join(os.getcwd(), 'saved_models')
model_name = 'keras_cifar10_trained_model.h5'

# The data, split between train and test sets:
(x_train, y_train), (x_test, y_test) = cifar10.load_data()
print('x_train shape:', x_train.shape)
print(x_train.shape[0], 'train samples')
print(x_test.shape[0], 'test samples')

y_train = keras.utils.to_categorical(y_train, num_classes)
y_test = keras.utils.to_categorical(y_test, num_classes)


def normalize_vector(x):
    z = K.sum(K.batch_flatten(K.square(x)), axis=1)
    while K.ndim(z) < K.ndim(x):
        z = K.expand_dims(z, axis=-1)
    return x / (K.sqrt(z))


def kld_(p, q):
    v = p * (K.log(p + K.constant(1e-8)) - K.log(q + K.constant(1e-8)))
    return K.sum(K.batch_flatten(v), axis=1, keepdims=True)


def loss_with_vat(target, output):
    normal_outputs = [K.stop_gradient(x) for x in model.outputs]
    d_list = [K.random_normal((32, 32, 3))] * batch_size
    ip = 1
    xi = 10
    eps = 2
    for _ in range(ip):
        new_inputs = [x + normalize_vector(d) * xi for (x, d) in zip(model.inputs, d_list)]
        new_outputs = [model.call(new_inputs)]
        klds = [K.sum(kld_(normal, new)) for normal, new in zip(normal_outputs, new_outputs)]
        kld = reduce(lambda t, x: t + x, klds, 0)
        d_list = [K.stop_gradient(d) for d in K.gradients(kld, d_list)]

    new_inputs = [x + normalize_vector(d) * eps for (x, d) in zip(model.inputs, d_list)]
    y_perturbations = model.call(new_inputs)
    klds = [K.mean(kld_(normal, new)) for normal, new in zip(normal_outputs, [y_perturbations])]
    kld = reduce(lambda t, x: t + x, klds, 0)
    return K.categorical_crossentropy(target, output) + kld / batch_size


input_layer = Input(x_train.shape[1:])
x = Convolution2D(128, (3, 3), padding='same')(input_layer)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)
x = Convolution2D(128, (3, 3), padding='same')(x)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)
x = Convolution2D(128, (3, 3), padding='valid')(x)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)

x = MaxPooling2D((2, 2), strides=(2, 2))(x)
x = Dropout(0.5)(x)

x = Convolution2D(256, (3, 3), padding='same')(x)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)
x = Convolution2D(256, (3, 3), padding='same')(x)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)
x = Convolution2D(256, (3, 3), padding='valid')(x)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)

x = MaxPooling2D((2, 2), strides=(2, 2))(x)
x = Dropout(0.5)(x)

x = Convolution2D(512, (3, 3), padding='same')(x)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)
x = Convolution2D(256, (1, 1), padding='same')(x)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)
x = Convolution2D(128, (1, 1), padding='valid')(x)
x = BatchNormalization()(x)
x = advanced_activations.LeakyReLU(alpha=0.1)(x)

x = pooling.GlobalAveragePooling2D()(x)

output = Dense(10, activation="softmax")(x)


def learning_rates(epoch):
    if epoch < epochs / 2:
        return 0.003
    else:
        return np.linspace(0.003, 0.0005, int(epochs / 2))[epoch]


opt = keras.optimizers.Adam(lr=0.003, beta_1=0.9, beta_2=0.999, epsilon=1e-08)
# lr_cb = keras.callbacks.LearningRateScheduler(lambda epoch: float(learning_rates(epoch)))

model = Model(input_layer, output)
model.summary()
model.compile(loss='categorical_crossentropy',
              optimizer=opt,
              metrics=['accuracy'])

x_train = x_train.astype('float32')
x_test = x_test.astype('float32')
x_train /= 255
x_test /= 255

print('Not using data augmentation.')
model.fit(x_train, y_train,
          batch_size=batch_size,
          epochs=epochs,
          validation_data=(x_test, y_test),
          shuffle=True, verbose=2)

# Save model and weights
if not os.path.isdir(save_dir):
    os.makedirs(save_dir)
model_path = os.path.join(save_dir, model_name)
model.save(model_path)
print('Saved trained model at %s ' % model_path)

# Score trained model.
scores = model.evaluate(x_test, y_test, verbose=1)
print('Test loss:', scores[0])
print('Test accuracy:', scores[1])
