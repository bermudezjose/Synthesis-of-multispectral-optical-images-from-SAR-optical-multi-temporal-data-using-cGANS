from __future__ import division
import os
import time
import glob
import tensorflow as tf
import numpy as np
from six.moves import xrange
from sklearn import preprocessing as pre
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
import scipy.io as io
import matplotlib.pyplot as plt
import keras
import matplotlib.pyplot as plt
from ops import *
from utils import *
from saveweigths import *
from skimage import exposure

class pix2pix(object):
    def __init__(self, sess, image_size=256, load_size=286,
                 batch_size=1, sample_size=1, output_size=256,
                 gf_dim=64, df_dim=64, L1_lambda=100,
                 input_c_dim=11, output_c_dim=7, dataset_name='facades',
                 checkpoint_dir=None, sample_dir=None, n_features=7,
                 n_classes=8, isTrain=True):
        """

        Args:
            sess: TensorFlow session
            batch_size: The size of batch. Should be specified before training.
            output_size: (optional) The resolution in pixels of the images. [256]
            gf_dim: (optional) Dimension of gen filters in first conv layer. [64]
            df_dim: (optional) Dimension of discrim filters in first conv layer. [64]
            input_c_dim: (optional) Dimension of input image color. For grayscale input, set to 1. [3]
            output_c_dim: (optional) Dimension of output image color. For grayscale input, set to 1. [3]
        """
        self.sess = sess
        self.is_grayscale = (input_c_dim == 1)
        self.batch_size = batch_size
        self.image_size = image_size
        self.load_size = load_size
        self.fine_size = image_size
        self.batch_size_classifier = 32
        self.n_features = n_features
        self.n_classes = n_classes
        self.dropout_rate = 0.3
        self.isTrain = isTrain
        self.sample_size = sample_size
        self.output_size = output_size
        self.sar_root_patch = '/mnt/Data/DataBases/RS/SAR/Campo Verde/npy_format/'
        self.opt_root_patch = '/mnt/Data/DataBases/RS/SAR/Campo Verde/LANDSAT/'
        self.sar_name = '14_31Jul_2016.npy'

        self.gf_dim = gf_dim
        self.df_dim = df_dim

        self.input_c_dim = input_c_dim
        self.output_c_dim = output_c_dim

        self.L1_lambda = L1_lambda

        # batch normalization : deals with poor initialization helps gradient flow
        self.r_bn = batch_norm(name='r_bn')
        self.d_bn1 = batch_norm(name='d_bn1')
        self.d_bn2 = batch_norm(name='d_bn2')
        self.d_bn3 = batch_norm(name='d_bn3')

        self.d_bn_e2 = batch_norm(name='d_bn_e2')
        self.d_bn_e3 = batch_norm(name='d_bn_e3')
        self.d_bn_e4 = batch_norm(name='d_bn_e4')
        self.d_bn_e5 = batch_norm(name='d_bn_e5')
        self.d_bn_e6 = batch_norm(name='d_bn_e6')
        self.d_bn_e7 = batch_norm(name='d_bn_e7')
        self.d_bn_e8 = batch_norm(name='d_bn_e8')

        self.d_bn_d1 = batch_norm(name='d_bn_d1')
        self.d_bn_d2 = batch_norm(name='d_bn_d2')
        self.d_bn_d3 = batch_norm(name='d_bn_d3')
        self.d_bn_d4 = batch_norm(name='d_bn_d4')
        self.d_bn_d5 = batch_norm(name='d_bn_d5')
        self.d_bn_d6 = batch_norm(name='d_bn_d6')
        self.d_bn_d7 = batch_norm(name='d_bn_d7')

        self.g_bn_e2 = batch_norm(name='g_bn_e2')
        self.g_bn_e3 = batch_norm(name='g_bn_e3')
        self.g_bn_e4 = batch_norm(name='g_bn_e4')
        self.g_bn_e5 = batch_norm(name='g_bn_e5')
        self.g_bn_e6 = batch_norm(name='g_bn_e6')
        self.g_bn_e7 = batch_norm(name='g_bn_e7')
        self.g_bn_e8 = batch_norm(name='g_bn_e8')

        self.g_bn_d1 = batch_norm(name='g_bn_d1')
        self.g_bn_d2 = batch_norm(name='g_bn_d2')
        self.g_bn_d3 = batch_norm(name='g_bn_d3')
        self.g_bn_d4 = batch_norm(name='g_bn_d4')
        self.g_bn_d5 = batch_norm(name='g_bn_d5')
        self.g_bn_d6 = batch_norm(name='g_bn_d6')
        self.g_bn_d7 = batch_norm(name='g_bn_d7')


        self.dataset_name = dataset_name
        self.checkpoint_dir = checkpoint_dir
        self.build_model()


    def build_model(self):

        self.dropout_g = tf.placeholder(tf.bool)
        self.dropout_d = tf.placeholder(tf.bool)
        self.bands_sar = 2
        self.sar = tf.placeholder(tf.float32,
                                  [self.batch_size, 3*self.image_size, 3*self.image_size, self.bands_sar],
                                   name='sar_images')
        self.opt = tf.placeholder(tf.float32,
                                 [self.batch_size, self.image_size, self.image_size, self.output_c_dim],
                                 name='opt_images')

        self.sar_resampling = lrelu(self.r_bn(conv2d(self.sar, self.bands_sar, d_h=3, d_w=3, name='sar_conv_resampling')))
        self.real_A = self.sar_resampling
        self.real_B = self.opt

        self.fake_B = self.generator(self.real_A)

        self.real_AB = tf.concat([self.real_A, self.real_B], 3)
        self.fake_AB = tf.concat([self.real_A, self.fake_B], 3)
        # self.descriptor, self.one_map_logits, self.d_logits
        # noise_real = tf.random_normal(
        #                               shape=tf.shape(self.real_AB),
        #                               mean=0.0,
        #                               stddev=0.05,
        #                               dtype=tf.float32,
        #                               )

        # noise_fake = tf.random_normal(
        #                               shape=tf.shape(self.fake_AB),
        #                               mean=0.0,
        #                               stddev=0.05,
        #                               dtype=tf.float32,
        #                               )

        # self.feature_real, self.D_logits_real, self.D_logits_class = self.discriminator(self.real_AB + noise_real, reuse=False)
        # self.feature_fake, self.D_logits_fake, self.D_logits_class_ = self.discriminator(self.fake_AB + noise_fake, reuse=True)
        self.feature_real, self.D_logits_real, self.D_logits_class = self.discriminator(self.real_AB, reuse=False)
        self.feature_fake, self.D_logits_fake, self.D_logits_class_ = self.discriminator(self.fake_AB, reuse=True)

        self.D_logits_real_flatten = tf.reshape(self.D_logits_real, [-1, 1])
        self.D_logits_fake_flatten = tf.reshape(self.D_logits_fake, [-1, 1])

        self.d_sum = tf.summary.histogram("d", self.feature_real)
        self.d__sum = tf.summary.histogram("d_", self.feature_fake)

        self.noise = tf.random_uniform(shape=tf.shape(self.D_logits_real_flatten),
                                       minval=0,
                                       maxval=0.2,
                                       dtype=tf.float32
                                       )

        # Calculate cross entropy
        # self.fcn_loss_fake, _, _ = cal_loss(self, logits=self.D_logits_class_, labels=self.labels)
        self.d_loss_real = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_logits_real_flatten, labels=tf.ones_like(self.D_logits_real_flatten)-self.noise))
        self.d_loss_fake = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_logits_fake_flatten, labels=tf.zeros_like(self.D_logits_fake_flatten)+self.noise))
        self.g_loss0 = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=self.D_logits_fake_flatten, labels=tf.ones_like(self.D_logits_fake_flatten)-self.noise)) 
        self.l1_loss = self.L1_lambda * tf.reduce_mean(tf.abs(self.real_B - self.fake_B))
        self.l2_loss = tf.reduce_mean(tf.nn.l2_loss(self.feature_real-self.feature_fake))/(self.image_size*self.image_size)
        # self.l2_loss = 100.0 * tf.reduce_mean(tf.abs(self.feature_real-self.feature_fake))
        self.g_loss = self.g_loss0 + self.l1_loss + self.l2_loss

        self.d_loss_real_sum = tf.summary.scalar("d_loss_real", self.d_loss_real)
        self.d_loss_fake_sum = tf.summary.scalar("d_loss_fake", self.d_loss_fake)

        self.d_loss = self.d_loss_real + self.d_loss_fake

        self.g_loss_sum = tf.summary.scalar("g_loss", self.g_loss)
        self.d_loss_sum = tf.summary.scalar("d_loss", self.d_loss)

        t_vars = tf.trainable_variables()

        self.d_vars = [var for var in t_vars if 'd_' in var.name]
        self.g_vars = [var for var in t_vars if 'g_' in var.name]
        self.saver = tf.train.Saver()


    def train(self, args):
        """Train pix2pix"""
        d_optim = tf.train.AdamOptimizer(args.lr, beta1=args.beta1) \
                          .minimize(self.d_loss, var_list=self.d_vars)
        g_optim = tf.train.AdamOptimizer(args.lr, beta1=args.beta1) \
                          .minimize(self.g_loss, var_list=self.g_vars)

        init_op = tf.global_variables_initializer()
        self.sess.run(init_op)

#        self.g_sum = tf.summary.merge([self.d__sum,
#            self.fake_B_sum, self.d_loss_fake_sum, self.g_loss_sum])
#        self.d_sum = tf.summary.merge([self.d_sum, self.d_loss_real_sum, self.d_loss_sum])
        self.writer = tf.summary.FileWriter("./logs", self.sess.graph)

        counter = 10
        start_time = time.time()

        if self.load(self.checkpoint_dir):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")

        for epoch in xrange(counter, args.epoch):
            # data_original = glob.glob('/mnt/Data/Pix2Pix_datasets/Campo_Verde/Training/*.npy')
            # data_fliped = glob.glob('/mnt/Data/Pix2Pix_datasets/Campo_Verde/Training_flip/*.npy')
            # data = data_original + data_fliped
            data_original = glob.glob('/mnt/Data/Pix2Pix_datasets/Campo_Verde/Training/*.npy')
            data = data_original
            plot_samples(self, data) 
            np.random.shuffle(data)
            batch_idxs = min(len(data), args.train_size) // self.batch_size
            Dloss = []
            Gloss = []
            L2loss = []
            L1loss = []
            for idx in xrange(0, batch_idxs):
                batch_images = load_data_Dic_Multiresolution(samples_list=data,
                                                             idxc=idx,
                                                             load_size=self.load_size,
                                                             fine_size=self.fine_size,
                                                             random_transformation=True,
                                                             multitemporal=False)

                sar_t0 = batch_images[0].reshape(self.batch_size, 3*self.image_size, 3*self.image_size, -1)
                opt_t0 = batch_images[1].reshape(self.batch_size, self.image_size, self.image_size, -1)
                # Update D network
                _, summary_str = self.sess.run([d_optim, self.d_sum],
                                               feed_dict={self.sar: sar_t0, self.opt: opt_t0, self.dropout_d: True, self.dropout_g: True})
                self.writer.add_summary(summary_str, epoch)
                

                # Update G network
                _ = self.sess.run([g_optim],
                                     feed_dict={ self.sar: sar_t0, self.opt: opt_t0, self.dropout_d: False, self.dropout_g: True})
#                self.writer.add_summary(summary_str, counter)

                # Run g_optim twice to make sure that d_loss does not go to zero (different from paper)
                _ = self.sess.run([g_optim],
                                  feed_dict={ self.sar: sar_t0, self.opt: opt_t0, self.dropout_d: False, self.dropout_g: True})
#                self.writer.add_summary(summary_str, counter)

                if np.mod(idx + 1, 100) == 0:
                    errD_fake = self.d_loss_fake.eval({ self.sar: sar_t0, self.opt: opt_t0, self.dropout_d: False, self.dropout_g: True})
                    errD_real = self.d_loss_real.eval({ self.sar: sar_t0, self.opt: opt_t0, self.dropout_d: False, self.dropout_g: True})
                    errG = self.g_loss.eval({ self.sar: sar_t0, self.opt: opt_t0, self.dropout_d: False, self.dropout_g: True})
                    errGl1 = self.l1_loss.eval({ self.sar: sar_t0, self.opt: opt_t0, self.dropout_d: False, self.dropout_g: True})
                    errGl2 = self.l2_loss.eval({ self.sar: sar_t0, self.opt: opt_t0, self.dropout_d: False, self.dropout_g: True})
                    Dloss.append(errD_fake+errD_real)
                    Gloss.append(errG)
                    L2loss.append(errGl2)
                    L1loss.append(errGl1)
                    print("Epoch: [%2d] [%4d/%4d] time: %4.4f, d_loss: %.8f, g_loss: %.8f, l1_loss: %.8f, l2_loss: %.8f" \
                        % (epoch, idx, batch_idxs,
                            time.time() - start_time, np.mean(Dloss), np.mean(Gloss), np.mean(L1loss), np.mean(L2loss)))
                    # print("Epoch: [%2d] [%4d/%4d] time: %4.4f, d_loss: %.8f, g_loss: %.8f , g_l2: %.8f" \
                    #     % (epoch, idx, batch_idxs,
                    #         time.time() - start_time, np.mean(Dloss), np.mean(Gloss), np.mean(L2loss)))

            self.save(args.checkpoint_dir, epoch)
        plt.pause()
    # Fine tuning
    def fine_tuning(self, args):
        """Optimize fcn"""
        # train_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,
                               # scope="g_class_map")
        # training_op = optimizer.minimize(loss, var_list=train_vars)
        # fcn_optim = tf.train.AdamOptimizer(0.001, beta1=args.beta1) \
        #                     .minimize(self.fcn_loss, var_list=self.fcn_vars)
        # d_classes
        train_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope="discriminator/d_classes|discriminator/d_d8")
        fcn_optim = tf.train.AdamOptimizer(0.0001, beta1=args.beta1) \
                            .minimize(self.fcn_loss_fake, var_list=train_vars)

        init_op = tf.global_variables_initializer()
        self.sess.run(init_op)

        self.writer = tf.summary.FileWriter("./logs", self.sess.graph)

        counter = 1
        start_time = time.time()

        labels_path = '/mnt/Data/DataBases/RS/SAR/Campo Verde/Labels_uint8/10_May_2016.tif'
        labels2new_labels, new_labels2labels = labels_look_table(labels_path)

        if self.load(self.checkpoint_dir):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")

        sample_dir_root = '/home/jose/Templates/Pix2Pix/pix2pix-tensorflow_jose/sample/'
        sample_dir = os.path.join(sample_dir_root, self.dataset_name)

        if not os.path.exists(sample_dir):
            os.makedirs(sample_dir)

        # Cambiar para los datos de Campo Verde
        datasets_root = '/mnt/Data/Pix2Pix_datasets/Semi_Exp/'
        dataset_name = '05may2016_C01_synthesize_fcn_BASELINE/'
        data_trn_list = glob.glob(datasets_root + dataset_name + 'Training/*.npy')
        data_val_list = glob.glob(datasets_root + dataset_name + 'Training/*.npy')
        data_test_list= glob.glob(datasets_root + dataset_name + 'Testing/*.npy')

        data_Dic = np.load(data_test_list[6]).item()
        tst_labels = np.array(data_Dic['labels'])
        tst_img_A = np.array(data_Dic['img_A']).astype('float32').reshape(1, 256, 256, self.input_c_dim)
        tst_img_A = np.concatenate((tst_img_A, tst_img_A), axis=0)
        tst_img_B = np.array(data_Dic['img_B']).astype('float32')
        fig = self.plot_patch(tst_img_B, n_fig="Testing Patch")
        fig.savefig(sample_dir + '/sample_original_tst.png', dpi=300)

        data_Dic = np.load(data_trn_list[6]).item()
        trn_labels = np.array(data_Dic['labels'])
        trn_img_A = np.array(data_Dic['img_A']).astype('float32').reshape(1, 256, 256, self.input_c_dim)
        trn_img_B = np.array(data_Dic['img_B']).astype('float32')
        fig = self.plot_patch(trn_img_B, n_fig="Training Patch")
        fig.savefig(sample_dir + '/sample_original_trn.png', dpi=300)

        # plt.figure("Testing Labels")
        # plt.imshow(tst_labels)
        # plt.show(block=False)
        # plt.figure("Training Labels")
        # plt.imshow(trn_labels)
        # plt.show(block=False)
        # plt.pause(0.5)

        Val_loss = []
        Trn_loss = []
        counter = 100
        fig5 = plt.figure('losses fcn')
        for epoch in xrange(args.epoch):
        # for epoch in xrange(1):

            G_gloss = []
            G_l1loss = []

            errorD = []
            errorG = []

            loss = []
            np.random.shuffle(data_trn_list)
            batch_idxs = min(len(data_trn_list), args.train_size)
            for idx in xrange(0, batch_idxs, self.batch_size):
            # for idx in xrange(0, 1):
                # TODO: Modify this
                img_A = []
                img_B = []
                labels = []
                beta = []
                if (idx + self.batch_size) > batch_idxs:
                    continue
                for img in range(self.batch_size):
                    
                    Data = load_data4FCN_CV(self,
                                            data_trn_list,
                                            sample_index=idx + img,
                                            labels2new_labels=labels2new_labels)
                    img_A.append(Data[0])
                    img_B.append(Data[1])
                    labels.append(Data[2])
                    beta.append(Data[3])
                if np.sum(beta) < 2:
                    continue
                batch_images = np.concatenate((np.array(img_A).reshape(self.batch_size, self.image_size, self.image_size, self.input_c_dim),
                                               np.array(img_B).reshape(self.batch_size, self.image_size, self.image_size, self.output_c_dim)),
                                              axis=3)
                labels = np.array(labels).reshape(self.batch_size, self.image_size, self.image_size)

                _, fcn_loss = self.sess.run([fcn_optim, self.fcn_loss_fake],
                                           feed_dict={self.real_data: batch_images, self.labels: labels, self.dropout_d: True, self.dropout_g: True})
                # fcn_loss = self.sess.run([self.fcn_loss_fake],
                #                            feed_dict={self.real_data: batch_images, self.labels: labels, self.dropout_d: True, self.dropout_g: True})
                # print (np.shape(fcn_loss), fcn_loss)
                loss.append(fcn_loss)
            print("Epoch --->", epoch)
            print("Loss epoch --->", np.mean(loss))            
            # Validation generated samples !!!
            # val_loss = validate_FCN_CV(self, data_test_list, labels2new_labels)
            val_loss = validate_FCN_CV_batchsize_discriminator(self, data_test_list, labels2new_labels)
            Val_loss.append(val_loss)
            print("Validation loss -->", val_loss)
            Trn_loss.append(np.mean(loss))
            errC_h = [Trn_loss, Val_loss]
            legends = ['trn loss', 'val loss']
            self.plot_loss(errC_h, legends, fig5)
            # plt.savefig(sample_dir + 'loss_classifier_generated_validation.png', dpi=600)
            print("-----------------------------------------------------")
            # self.save(args.checkpoint_dir, counter)
            counter += 1
            tst_opt_generated = self.sess.run(self.fake_B,
                                              feed_dict={self.real_A: tst_img_A[:self.batch_size], self.dropout_g:True})
            tst_opt_generated = tst_opt_generated[0].reshape(256, 256, self.n_features)
            fig = self.plot_patch(tst_opt_generated, n_fig="Generated: test")

            



    def plot_loss(self, data, legends, fig):
        # n_graph = len(legends)
        colors = ['r-', 'b-', 'g-', 'y-']
        sh = np.shape(data)
        n_dim = np.shape(sh)[0]
        if n_dim < 1:
            return 0
        ax = fig.add_subplot(111)
        ax.legend(legends, loc='upper right', fontsize=14)
        x = np.arange(len(data[0]))
        # print (x)
        for i in range(n_dim):
            y = data[i]       
            line, = ax.plot(x, y, colors[i])
            # fig.draw()
            # line, = ax.plot(x, y[1], 'b-')
            fig.show()
            plt.pause(0.001)
        return plt


    # def discriminator(self, image, y=None, reuse=False):

    #     with tf.variable_scope("discriminator") as scope:

    #         # image is 256 x 256 x (input_c_dim + output_c_dim)
    #         if reuse:
    #             tf.get_variable_scope().reuse_variables()
    #         else:
    #             assert tf.get_variable_scope().reuse == False

    #         d_e1 = conv2dlayer(image, self.df_dim, name='d_e1_conv') # 64x2x5x5+64 = 3,264
    #         # e1 is (128 x 128 x self.gf_dim)
    #         d_e2 = self.d_bn_e2(conv2dlayer(lrelu(d_e1), self.df_dim*2, name='d_e2_conv')) # (2x64)x64x5x5 + (2x64) = 204,928
    #         # e2 is (64 x 64 x self.gf_dim*2)
    #         d_e3 = self.d_bn_e3(conv2dlayer(lrelu(d_e2), self.df_dim*4, name='d_e3_conv')) # (4x64)x(2x64)x5x5 + (4x64) = 819,456
    #         # e3 is (32 x 32 x self.gf_dim*4)
    #         d_e4 = self.d_bn_e4(conv2dlayer(lrelu(d_e3), self.df_dim*8, name='d_e4_conv')) # (8x64)x(4x64)x5x5 + (8x64) = 3,277,312
    #         # e4 is (16 x 16 x self.gf_dim*8)
    #         d_e5 = self.d_bn_e5(conv2dlayer(lrelu(d_e4), self.df_dim*8, name='d_e5_conv')) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
    #         # e5 is (8 x 8 x self.gf_dim*8)
    #         d_e6 = self.d_bn_e6(conv2dlayer(lrelu(d_e5), self.df_dim*8, name='d_e6_conv')) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
    #         # e6 is (4 x 4 x self.gf_dim*8)
    #         d_e7 = self.d_bn_e7(conv2dlayer(lrelu(d_e6), self.df_dim*8, name='d_e7_conv')) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
    #         # e7 is (2 x 2 x self.gf_dim*8)
    #         d_e8 = self.d_bn_e8(conv2dlayer(lrelu(d_e7), self.df_dim*8, name='d_e8_conv')) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
    #         # e8 is (1 x 1 x self.gf_dim*8)

    #         self.d_d1= deconv2dlayer(tf.nn.relu(d_e8), self.df_dim*8, name='d_d1') # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
    #         d_d1 = tf.layers.dropout(self.d_bn_d1(self.d_d1), 0.5, training=self.dropout_d)
    #         d_d1 = tf.concat([d_d1, d_e7], 3)
    #         # d1 is (2 x 2 x self.gf_dim*8*2)

    #         self.d_d2 = deconv2dlayer(tf.nn.relu(d_d1), self.df_dim*8, name='d_d2') # (2*8x64)x(8x64)x5x5 + (2*8x64) = 13,108,224
    #         d_d2 = tf.layers.dropout(self.d_bn_d2(self.d_d2), 0.5, training=self.dropout_d)
    #         d_d2 = tf.concat([d_d2, d_e6], 3)
    #         # d2 is (4 x 4 x self.gf_dim*8*2)

    #         self.d_d3= deconv2dlayer(tf.nn.relu(d_d2), self.df_dim*8, name='d_d3') # (2*8x64)x(8x64)x5x5 + (2*8x64) = 13,108,224
    #         d_d3 = tf.layers.dropout(self.d_bn_d3(self.d_d3), 0.5, training=self.dropout_d)
    #         d_d3 = tf.concat([d_d3, d_e5], 3)
    #         # d3 is (8 x 8 x self.gf_dim*8*2)

    #         self.d_d4 = deconv2dlayer(tf.nn.relu(d_d3), self.df_dim*8, name='d_d4') # (2*8x64)x(8x64)x5x5 + (2*8x64) = 13,108,224
    #         d_d4 = self.d_bn_d4(self.d_d4)
    #         d_d4 = tf.concat([d_d4, d_e4], 3)
    #         # d4 is (16 x 16 x self.gf_dim*8*2)

    #         self.d_d5 = deconv2dlayer(tf.nn.relu(d_d4), self.df_dim*4, name='d_d5') # (2*4x64)x(8x64)x5x5 + (2*4x64) = 6,554,112
    #         d_d5 = self.d_bn_d5(self.d_d5)
    #         d_d5 = tf.concat([d_d5, d_e3], 3)
    #         # d5 is (32 x 32 x self.gf_dim*4*2)

    #         self.d_d6 = deconv2dlayer(tf.nn.relu(d_d5), self.df_dim*2, name='d_d6') # (2*2x64)x(4x64)x5x5 + (2*2x64) = 1,638,656
    #         d_d6 = self.g_bn_d6(self.d_d6)
    #         d_d6 = tf.concat([d_d6, d_e2], 3)
    #         # d_d6_pool = tf.layers.max_pooling2d(inputs=d_d6, pool_size=[4, 4], strides=4)
    #         # d6 is (64 x 64 x self.gf_dim*2*2)

    #         self.d_d7 = deconv2dlayer(tf.nn.relu(d_d6), self.df_dim, name='d_d7') # (2*1x64)x(2x64)x5x5 + (2*1x64) = 409,728
    #         d_d7 = self.d_bn_d7(self.d_d7)
    #         d_d7 = tf.concat([d_d7, d_e1], 3)
    #         # d_d7_pool = tf.layers.max_pooling2d(inputs=d_d7, pool_size=[2,2], strides=2)
    #         # d7 is (128 x 128 x self.gf_dim*1*2)

    #         self.descriptor = deconv2dlayer(tf.nn.relu(d_d7), self.df_dim, name='d_d8') # (1*1x64)x(1x7)x5x5 + (1*1x7) = 11,207
    #         # self.descriptor = tf.concat([self.d_d8, d_d7_pool, d_d6_pool], 3)

    #         # d8 is (256 x 256 x output_c_dim)

    #         # adding classification layer
    #         # self.d9 = deconv2dlayer(d7, self.n_classes, name='f_class_map', trainable=self.isTrain)
    #         # self.d9 = deconv2dlayer(tf.nn.relu(d7), self.n_classes, name='f_class_map', trainable=self.isTrain)
    #         # drop8 = tf.layers.dropout(self.d8, 0.5, training=self.dropout)
    #         # self.d9 = deconv2dlayer(drop8, self.n_classes, name='f_class_map', trainable=self.isTrain)
    #         self.one_map = conv2dlayer(self.descriptor, 1, k_h=1, k_w=1, d_h=1, d_w=1, name='d_map')
    #         self.d_logits = conv2dlayer(self.descriptor, self.n_classes, k_h=1, k_w=1, d_h=1, d_w=1, name='d_classes')

    #         return self.descriptor, self.one_map, self.d_logits

    def discriminator(self, image, y=None, reuse=False):

        with tf.variable_scope("discriminator") as scope:

            # image is 256 x 256 x (input_c_dim + output_c_dim)
            if reuse:
                tf.get_variable_scope().reuse_variables()
            else:
                assert tf.get_variable_scope().reuse == False

            d_e1 = conv2dlayer(image, self.df_dim, k_h=5, k_w=5, name='d_e1_conv')
            # e1 is (128 x 128 x self.gf_dim)
            d_e2 = self.d_bn_e2(conv2dlayer(lrelu(d_e1), self.df_dim*2, k_h=5, k_w=5, name='d_e2_conv'))
            # e2 is (64 x 64 x self.gf_dim*2)
            d_e3 = self.d_bn_e3(conv2dlayer(lrelu(d_e2), self.df_dim*4, k_h=5, k_w=5, name='d_e3_conv'))
            # e3 is (32 x 32 x self.gf_dim*4)
            d_e4 = self.d_bn_e4(conv2dlayer(lrelu(d_e3), self.df_dim*8, k_h=5, k_w=5, name='d_e4_conv'))
            # e4 is (16 x 16 x self.gf_dim*8)

            self.d_d1= deconv2dlayer(tf.nn.relu(d_e4), self.df_dim*4, k_h=5, k_w=5, name='d_d1')
            d_d1 = self.d_bn_d1(self.d_d1)
            d_d1 = tf.concat([d_d1, d_e3], 3)
            # 32 x 32

            self.d_d2 = deconv2dlayer(tf.nn.relu(d_d1), self.df_dim*2, k_h=5, k_w=5, name='d_d2')
            d_d2 = self.d_bn_d2(self.d_d2)
            d_d2 = tf.concat([d_d2, d_e2], 3)
            # 64 x 64

            self.d_d3= deconv2dlayer(tf.nn.relu(d_d2), self.df_dim*1, k_h=5, k_w=5, name='d_d3')
            d_d3 = self.d_bn_d3(self.d_d3)
            d_d3 = tf.concat([d_d3, d_e1], 3)
            # 128 x 128

            self.descriptor = deconv2dlayer(tf.nn.relu(d_d3), self.df_dim*1, k_h=5, k_w=5, name='d_descriptors')
            # d_d4 = self.d_bn_d4(self.d_d4)
            # 256 x 256

            # self.descriptor = deconv2dlayer(tf.nn.relu(d_d4), 1, k_h=1, k_w=1, name='d_descriptors')
            self.one_map_logits = conv2dlayer(self.descriptor, 1, k_h=1, k_w=1, d_h=1, d_w=1, name='d_map')
            self.d_logits = conv2dlayer(self.descriptor, self.n_classes, k_h=1, k_w=1, d_h=1, d_w=1, name='d_classes')

            return self.descriptor, self.one_map_logits, self.d_logits
            # self.descriptor, self.one_map_logits, self.d_logits
            # self.d_d5 = deconv2dlayer(tf.nn.relu(d_d4), self.df_dim*4, name='d_d5')
            # d_d5 = self.d_bn_d5(self.d_d5)
            # d_d5_up = deconv2dlayer(d_d5, self.df_dim*4, k_h=8, k_w=8, d_h=8, d_w=8, name='d_d5_up')

            # self.d_d6 = deconv2dlayer(tf.nn.relu(d_d5), self.df_dim*2, name='d_d6')
            # d_d6 = self.g_bn_d6(self.d_d6)
            # d_d6_up = deconv2dlayer(d_d6, self.df_dim*2, k_h=4, k_w=4, d_h=4, d_w=4, name='d_d6_up')

            # self.d_d7 = deconv2dlayer(tf.nn.relu(d_d6), self.df_dim, name='d_d7')
            # d_d7 = self.d_bn_d7(self.d_d7)
            # d_d7_up = deconv2dlayer(d_d7, self.df_dim, k_h=2, k_w=2, d_h=2, d_w=2, name='d_d7_up')

            


    def generator(self, image, y=None):
        with tf.variable_scope("generator") as scope:

            s = self.output_size
            s2, s4, s8, s16, s32, s64, s128 = int(s/2), int(s/4), int(s/8), int(s/16), int(s/32), int(s/64), int(s/128)

            e1 = conv2dlayer(image, self.gf_dim, name='g_e1_conv', trainable=self.isTrain) # 64x2x5x5+64 = 3,264
            # e1 is (128 x 128 x self.gf_dim)
            e2 = self.g_bn_e2(conv2dlayer(lrelu(e1), self.gf_dim*2, name='g_e2_conv', trainable=self.isTrain)) # (2x64)x64x5x5 + (2x64) = 204,928
            # e2 is (64 x 64 x self.gf_dim*2)
            e3 = self.g_bn_e3(conv2dlayer(lrelu(e2), self.gf_dim*4, name='g_e3_conv', trainable=self.isTrain)) # (4x64)x(2x64)x5x5 + (4x64) = 819,456
            # e3 is (32 x 32 x self.gf_dim*4)
            e4 = self.g_bn_e4(conv2dlayer(lrelu(e3), self.gf_dim*8, name='g_e4_conv', trainable=self.isTrain)) # (8x64)x(4x64)x5x5 + (8x64) = 3,277,312
            # e4 is (16 x 16 x self.gf_dim*8)
            e5 = self.g_bn_e5(conv2dlayer(lrelu(e4), self.gf_dim*8, name='g_e5_conv', trainable=self.isTrain)) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
            # e5 is (8 x 8 x self.gf_dim*8)
            e6 = self.g_bn_e6(conv2dlayer(lrelu(e5), self.gf_dim*8, name='g_e6_conv', trainable=self.isTrain)) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
            # e6 is (4 x 4 x self.gf_dim*8)
            e7 = self.g_bn_e7(conv2dlayer(lrelu(e6), self.gf_dim*8, name='g_e7_conv', trainable=self.isTrain)) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
            # e7 is (2 x 2 x self.gf_dim*8)
            e8 = self.g_bn_e8(conv2dlayer(lrelu(e7), self.gf_dim*8, name='g_e8_conv', trainable=self.isTrain)) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
            # e8 is (1 x 1 x self.gf_dim*8)

            self.d1= deconv2dlayer(tf.nn.relu(e8), self.gf_dim*8, name='g_d1', trainable=self.isTrain) # (8x64)x(8x64)x5x5 + (8x64) = 6,554,112
            d1 = tf.layers.dropout(self.g_bn_d1(self.d1), 0.5, training=self.dropout_g)
            d1 = tf.concat([d1, e7], 3)
            # d1 is (2 x 2 x self.gf_dim*8*2)

            self.d2 = deconv2dlayer(tf.nn.relu(d1), self.gf_dim*8, name='g_d2', trainable=self.isTrain) # (2*8x64)x(8x64)x5x5 + (2*8x64) = 13,108,224
            d2 = tf.layers.dropout(self.g_bn_d2(self.d2), 0.5, training=self.dropout_g)
            d2 = tf.concat([d2, e6], 3)
            # d2 is (4 x 4 x self.gf_dim*8*2)

            self.d3= deconv2dlayer(tf.nn.relu(d2), self.gf_dim*8, name='g_d3', trainable=self.isTrain) # (2*8x64)x(8x64)x5x5 + (2*8x64) = 13,108,224
            d3 = tf.layers.dropout(self.g_bn_d3(self.d3), 0.5, training=self.dropout_g)
            d3 = tf.concat([d3, e5], 3)
            # d3 is (8 x 8 x self.gf_dim*8*2)

            self.d4 = deconv2dlayer(tf.nn.relu(d3), self.gf_dim*8, name='g_d4', trainable=self.isTrain) # (2*8x64)x(8x64)x5x5 + (2*8x64) = 13,108,224
            d4 = self.g_bn_d4(self.d4)
            d4 = tf.concat([d4, e4], 3)
            # d4 is (16 x 16 x self.gf_dim*8*2)

            self.d5 = deconv2dlayer(tf.nn.relu(d4), self.gf_dim*4, name='g_d5', trainable=self.isTrain) # (2*4x64)x(8x64)x5x5 + (2*4x64) = 6,554,112
            d5 = self.g_bn_d5(self.d5)
            d5 = tf.concat([d5, e3], 3)
            # d5 is (32 x 32 x self.gf_dim*4*2)

            self.d6 = deconv2dlayer(tf.nn.relu(d5), self.gf_dim*2, name='g_d6', trainable=self.isTrain) # (2*2x64)x(4x64)x5x5 + (2*2x64) = 1,638,656
            d6 = self.g_bn_d6(self.d6)
            d6 = tf.concat([d6, e2], 3)
            # d6 is (64 x 64 x self.gf_dim*2*2)

            self.d7 = deconv2dlayer(tf.nn.relu(d6), self.gf_dim, name='g_d7', trainable=self.isTrain) # (2*1x64)x(2x64)x5x5 + (2*1x64) = 409,728
            d7 = self.g_bn_d7(self.d7)
            d7 = tf.concat([d7, e1], 3)
            # d7 is (128 x 128 x self.gf_dim*1*2)

            self.d8 = deconv2dlayer(tf.nn.relu(d7), self.output_c_dim, name='g_d8', trainable=self.isTrain) # (1*1x64)x(1x7)x5x5 + (1*1x7) = 11,207
            # d8 is (256 x 256 x output_c_dim)

            return tf.nn.tanh(self.d8)


    def save(self, checkpoint_dir, step):
        model_name = "pix2pix.model"
        model_dir = "%s_%s_%s" % (self.dataset_name, self.batch_size, self.output_size)
        checkpoint_dir = os.path.join(checkpoint_dir, model_dir)

        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

        self.saver.save(self.sess,
                        os.path.join(checkpoint_dir, model_name),
                        global_step=step)
        print "Saving checkpoint!"
#        self.saver.save(self.sess, checkpoint_dir +'/my-model')
#        self.saver.export_meta_graph(filename=checkpoint_dir +'/my-model.meta')

    def load(self, checkpoint_dir):
#        return False
        print(" [*] Reading checkpoint...")
#
        model_dir = "%s_%s_%s" % (self.dataset_name, self.batch_size, self.output_size)
        checkpoint_dir = os.path.join(checkpoint_dir, model_dir)
        print(checkpoint_dir)
#2832, 2665,
#        new_placeholder = tf.placeholder(tf.float32, shape=[self.batch_size, 2831, 2665,
#                                         self.input_c_dim + self.output_c_dim], name='inputs_new_name')
#        self.saver = tf.train.import_meta_graph(checkpoint_dir +'/my-model.meta', input_map={"real_A_and_B_images:0": new_placeholder})
##        self.saver = tf.train.import_meta_graph(checkpoint_dir +'/my-model.meta')
#        self.saver.restore(self.sess, checkpoint_dir +'/my-model')
#
        ckpt = tf.train.get_checkpoint_state(checkpoint_dir)
        if ckpt and ckpt.model_checkpoint_path:
            ckpt_name = os.path.basename(ckpt.model_checkpoint_path)
            self.saver.restore(self.sess, os.path.join(checkpoint_dir, ckpt_name))
#            self.saver.export_meta_graph(filename='my-model.meta')
#            print 'model convertion success'
#            self.saver = tf.import_graph_def(os.path.join(checkpoint_dir, ckpt_name), input_map={"real_A_and_B_images:0": new_placeholder})
            return True
        else:
            return False

    def test(self, args):
        """Test pix2pix"""
        init_op = tf.global_variables_initializer()
        self.sess.run(init_op)

        sample_files = sorted(glob.glob('/home/jose/Templates/Pix2Pix/pix2pix-tensorflow_jose/datasets/'+self.dataset_name+'/test/*.npy'))

        # change this directoty

        # sort testing input
        n = [int(i) for i in map(lambda x: x.split('/')[-1].split('.npy')[0], sample_files)]
        sample_files = [x for (y, x) in sorted(zip(n, sample_files))]


        # load testing input
        print("Loading testing images ...")
        sample_images = [load_data(sample_file, is_test=True) for sample_file in sample_files]

#        if (self.is_grayscale):
#            sample_images = np.array(sample).astype(np.float32)[:, :, :, None]
#        else:
#            sample_images = np.array(sample).astype(np.float32)

        sample_images = [sample_images[i:i+self.batch_size]
                         for i in xrange(0, len(sample_images), self.batch_size)]
        sample_images = np.array(sample_images)
        print(sample_images.shape)

        start_time = time.time()
        if self.load(self.checkpoint_dir):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")

        for i, sample_image in enumerate(sample_images):
            idx = i+1
            print("sampling image ", idx)
            samples = self.sess.run(
                self.fake_B_sample,
                feed_dict={self.real_data: sample_image}
            )
            print samples.shape
            output_folder = '/home/jose/Templates/'
            np.save(output_folder+str(i), samples.reshape(256, 256, 7))
#            save_images(samples, [self.batch_size, 1],
#                        './{}/test_{:04d}.png'.format(args.test_dir, idx))
    def generate_image(self, args):
        print args
        output_folder = '/home/jose/Templates/Pix2Pix/pix2pix-tensorflow_jose/'
        init_op = tf.global_variables_initializer()
        self.sess.run(init_op)
        print(" [*] Load SUCCESS")
        if self.load(self.checkpoint_dir):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")
        print args.experiment_type
        if args.experiment_type is 'case_A':
            
            path_dataset = '/mnt/Data/Pix2Pix_datasets/Campo_Verde/'
            scaler_sar_t0 = joblib.load(path_dataset + "sar_may2016_10m_scaler.pkl")
            scaler_opt_t0 = joblib.load(path_dataset + "opt_may2016_scaler.pkl")
            scaler_sar_t1 = joblib.load(path_dataset + "sar_may2017_10m_scaler.pkl")
            scaler_opt_t1 = joblib.load(path_dataset + "opt_may2017_scaler.pkl")    
            
            print 'Case A ...'
            print 'generating image for_' + args.dataset_name
            sar_img_name_t0 = '10_08May_2016.npy'
            sar_img_name_t1 = '20170520.npy'
            sar_path_t0=self.sar_root_patch + sar_img_name_t0
            sar_path_t1=self.sar_root_patch + sar_img_name_t1
            sar_t0 = np.load(sar_path_t0)
            sar_t1 = np.load(sar_path_t1)
            sar_t0[sar_t0 > 1.0] = 1.0
            sar_t1[sar_t1 > 1.0] = 1.0
            num_rows, num_cols, num_bands = sar_t0.shape
            print('sar_t0.shape --->', sar_t0.shape)
            sar_t0 = sar_t0.reshape(num_rows * num_cols, -1)
            sar_t1 = sar_t1.reshape(num_rows * num_cols, -1)
            sar_t0 = np.float32(scaler_sar_t0.transform(sar_t0))
            sar_t1 = np.float32(scaler_sar_t1.transform(sar_t1))
            SAR_t0 = sar_t0.reshape(1, num_rows, num_cols, num_bands)
            SAR_t1 = sar_t1.reshape(1, num_rows, num_cols, num_bands)

            opt_name_t1 = '20170524/'
            opt_path_t1=self.opt_root_patch + opt_name_t1
            opt_t1, _ = load_landsat(opt_path_t1)
            opt_t1[np.isnan(opt_t1)] = 0.0
            print("opt_t1 -->", opt_t1.shape)
            num_rows, num_cols, num_bands = opt_t1.shape
            opt_t1 = opt_t1.reshape(num_rows * num_cols, self.output_c_dim)
            opt_t1 = np.float32(scaler_opt_t1.transform(opt_t1))
            opt_t1 = opt_t1.reshape(num_rows, num_cols, self.output_c_dim)
            
            OPT_t1 = opt_t1.reshape(1, num_rows, num_cols, -1)
            fake_opt = np.zeros((num_rows, num_cols, self.output_c_dim),
                            dtype='float32')
            
            stride = 3 * 64
            pad = (3 * self.image_size - stride) // 2
            for row in range(0, 3*num_rows, stride):
                for col in range(0, 3*num_cols, stride):
                    if (row + 3*self.image_size <= 3*num_rows) and (col+3*self.image_size <= 3*num_cols):

                        print row + pad, col + 3*self.image_size - pad
                        sar_t0_patch = SAR_t0[:, row:row+3*self.image_size, col:col+3*self.image_size]
                        sample = self.sess.run(self.fake_B,
                                               feed_dict={ self.sar: sar_t0_patch, self.dropout_d: False, self.dropout_g: True})
                        print sample.shape
                        fake_opt[row//3+pad//3:row//3+self.image_size-pad//3, col//3+pad//3:col//3+self.image_size-pad//3] = sample[0, pad//3:self.image_size-pad//3, pad//3:self.image_size-pad//3]
                    elif col+3*self.image_size <= 3*num_cols:
                        sar_t0_patch = SAR_t0[:, 3*num_rows-3*self.image_size-1:3*num_rows, col:col+3*self.image_size]
                        # print(sample_image.shape)
                        sample = self.sess.run(self.fake_B,
                                               feed_dict={ self.sar: sar_t0_patch, self.dropout_d: False, self.dropout_g: True})
                        print sample.shape
                        fake_opt[row//3+pad//3:num_rows, col//3+pad//3:col//3+self.image_size-pad//3] = sample[0, self.image_size-num_rows+row//3+pad//3:self.image_size, pad//3:self.image_size-pad//3]
                    elif row+self.image_size <= num_rows:
                        print col
                        sar_t0_patch = SAR_t0[:, row:row+3*self.image_size, 3*num_cols-3*self.image_size:3*num_cols]
                        sample = self.sess.run(self.fake_B,
                                               feed_dict={ self.sar: sar_t0_patch, self.dropout_d: False, self.dropout_g: True})
                        fake_opt[row//3+pad//3:row//3+self.image_size-pad//3, col//3+pad//3:num_cols] = sample[0, pad//3:self.image_size-pad//3, self.image_size-num_cols+col//3+pad//3:self.image_size]

            np.save(self.dataset_name + '_fake_opt', fake_opt)


    def generate_features(self, args):
        print args
        output_folder = '/home/jose/Templates/Pix2Pix/pix2pix-tensorflow_jose/'
        init_op = tf.global_variables_initializer()
        self.sess.run(init_op)
        print(" [*] Load SUCCESS")
        if self.load(self.checkpoint_dir):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")
        print args.experiment_type
        if args.experiment_type is 'case_A':
            # loading scalers ...
            path_dataset = '/mnt/Data/Pix2Pix_datasets/Campo_Verde/'
            scaler_sar_t0 = joblib.load(path_dataset + "sar_may2016_10m_scaler.pkl")
            scaler_opt_t0 = joblib.load(path_dataset + "opt_may2016_scaler.pkl")
            scaler_sar_t1 = joblib.load(path_dataset + "sar_may2017_10m_scaler.pkl")
            scaler_opt_t1 = joblib.load(path_dataset + "opt_may2017_scaler.pkl")    
            
            print 'Case A ...'
            print 'generating image for_' + args.dataset_name
            sar_img_name_t0 = '10_08May_2016.npy'
            sar_img_name_t1 = '20170520.npy'
            sar_path_t0=self.sar_root_patch + sar_img_name_t0
            sar_path_t1=self.sar_root_patch + sar_img_name_t1
            sar_t0 = np.load(sar_path_t0)
            sar_t1 = np.load(sar_path_t1)
            sar_t0[sar_t0 > 1.0] = 1.0
            sar_t1[sar_t1 > 1.0] = 1.0
            num_rows, num_cols, num_bands = sar_t0.shape
            print('sar_t0.shape --->', sar_t0.shape)
            sar_t0 = sar_t0.reshape(num_rows * num_cols, -1)
            sar_t1 = sar_t1.reshape(num_rows * num_cols, -1)
            sar_t0 = np.float32(scaler_sar_t0.transform(sar_t0))
            sar_t1 = np.float32(scaler_sar_t1.transform(sar_t1))
            SAR_t0 = sar_t0.reshape(1, num_rows, num_cols, num_bands)
            SAR_t1 = sar_t1.reshape(1, num_rows, num_cols, num_bands)

            opt_name_t0 = '20160505/'
            opt_path_t0=self.opt_root_patch + opt_name_t0
            opt_t0, _ = load_landsat(opt_path_t0)
            opt_t0[np.isnan(opt_t0)] = 0.0
            print("opt_t0 -->", opt_t0.shape)
            num_rows, num_cols, num_bands = opt_t0.shape
            opt_t0 = opt_t0.reshape(num_rows * num_cols, self.output_c_dim)
            opt_t0 = np.float32(scaler_opt_t0.transform(opt_t0))
            opt_t0 = opt_t0.reshape(num_rows, num_cols, self.output_c_dim)
            OPT_t0 = opt_t0.reshape(1, num_rows, num_cols, -1)

            opt_name_t1 = '20170524/'
            opt_path_t1=self.opt_root_patch + opt_name_t1
            opt_t1, _ = load_landsat(opt_path_t1)
            opt_t1[np.isnan(opt_t1)] = 0.0
            print("opt_t1 -->", opt_t1.shape)
            num_rows, num_cols, num_bands = opt_t1.shape
            opt_t1 = opt_t1.reshape(num_rows * num_cols, self.output_c_dim)
            opt_t1 = np.float32(scaler_opt_t1.transform(opt_t1))
            opt_t1 = opt_t1.reshape(num_rows, num_cols, self.output_c_dim)            
            OPT_t1 = opt_t1.reshape(1, num_rows, num_cols, -1)

            fake_opt = np.zeros((num_rows, num_cols, 64),
                            dtype='float32')
            
            stride = 3 * 64
            pad = (3 * self.image_size - stride) // 2
            for row in range(0, 3*num_rows, stride):
                for col in range(0, 3*num_cols, stride):
                    if (row + 3*self.image_size <= 3*num_rows) and (col+3*self.image_size <= 3*num_cols):

                        # print row + pad, col + 3*self.image_size - pad
                        sar_t0_patch = SAR_t0[:, row:row+3*self.image_size, col:col+3*self.image_size]
                        opt_t0_patch = OPT_t0[:, row//3:row//3+self.image_size, col//3:col//3+self.image_size]
                        sample = self.sess.run(self.feature_fake,
                                               feed_dict={ self.sar: sar_t0_patch, self.opt: opt_t0_patch, self.dropout_d: False, self.dropout_g: True})
                        # print (sample.shape)
                        fake_opt[row//3+pad//3:row//3+self.image_size-pad//3, col//3+pad//3:col//3+self.image_size-pad//3] = sample[0, pad//3:self.image_size-pad//3, pad//3:self.image_size-pad//3]
                    elif col+3*self.image_size <= 3*num_cols:
                        sar_t0_patch = SAR_t0[:, 3*num_rows-3*self.image_size-1:3*num_rows, col:col+3*self.image_size]
                        opt_t0_patch = OPT_t0[:, num_rows-self.image_size:num_rows, col//3:col//3+self.image_size]
                        # print(sample_image.shape)
                        sample = self.sess.run(self.feature_fake,
                                               feed_dict={ self.sar: sar_t0_patch, self.opt: opt_t0_patch, self.dropout_d: False, self.dropout_g: True})
                        # print (sample.shape)
                        fake_opt[row//3+pad//3:num_rows, col//3+pad//3:col//3+self.image_size-pad//3] = sample[0, self.image_size-num_rows+row//3+pad//3:self.image_size, pad//3:self.image_size-pad//3]
                    elif row+3*self.image_size <= 3*num_rows:
                        # print col
                        sar_t0_patch = SAR_t0[:, row:row+3*self.image_size, 3*num_cols-3*self.image_size:3*num_cols]
                        opt_t0_patch = OPT_t0[:, row//3:row//3+self.image_size, num_cols-self.image_size:num_cols]
                        sample = self.sess.run(self.feature_fake,
                                               feed_dict={ self.sar: sar_t0_patch, self.opt: opt_t0_patch, self.dropout_d: False, self.dropout_g: True})
                        fake_opt[row//3+pad//3:row//3+self.image_size-pad//3, col//3+pad//3:num_cols] = sample[0, pad//3:self.image_size-pad//3, self.image_size-num_cols+col//3+pad//3:self.image_size]

            np.save(self.dataset_name + '_fake_opt', fake_opt)


    def generate_classification_map(self, args):
        print args
        output_folder = '/home/jose/Templates/Pix2Pix/pix2pix-tensorflow_jose/'
        init_op = tf.global_variables_initializer()
        self.sess.run(init_op)
        print(" [*] Load SUCCESS")
        if self.load(self.checkpoint_dir):
            print(" [*] Load SUCCESS")
        else:
            print(" [!] Load failed...")
        print args.experiment_type
        if args.experiment_type is 'case_A':
            scaler_sar_t0 = joblib.load("sar_may2016_scaler.pkl")
            scaler_sar_t1 = joblib.load("sar_may2017_scaler.pkl")
            scaler_opt_t1 = joblib.load("opt_may2017_scaler.pkl")
            print 'Case A ...'
            print 'generating classification map for_' + args.dataset_name
            sar_img_name_t0 = '10_08May_2016.npy'
            sar_img_name_t1 = '20170520.npy'
            sar_path_t0=self.sar_root_patch + sar_img_name_t0
            sar_path_t1=self.sar_root_patch + sar_img_name_t1
            sar_t0 = np.load(sar_path_t0)
            sar_t1 = np.load(sar_path_t1)
            sar_t0 = resampler(sar_t0, 'float32')
            sar_t1 = resampler(sar_t1, 'float32')
            sar_t0[sar_t0 > 1.0] = 1.0
            sar_t1[sar_t1 > 1.0] = 1.0
            num_rows, num_cols, num_bands = sar_t0.shape
            print('sar_t0.shape --->', sar_t0.shape)
            sar_t0 = sar_t0.reshape(num_rows * num_cols, num_bands)
            sar_t1 = sar_t1.reshape(num_rows * num_cols, num_bands)
            sar_t0 = np.float32(scaler_sar_t0.transform(sar_t0))
            sar_t1 = np.float32(scaler_sar_t1.transform(sar_t1))
            sar_t0 = sar_t0.reshape(num_rows, num_cols, num_bands)
            sar_t1 = sar_t1.reshape(num_rows, num_cols, num_bands)

            opt_name_t1 = '20170524/'
            opt_path_t1=self.opt_root_patch + opt_name_t1
            opt_t1, _ = load_landsat(opt_path_t1)
            opt_t1[np.isnan(opt_t1)] = 0.0
            print("opt_t1 -->", opt_t1.shape)
            opt_t1 = opt_t1.reshape(num_rows * num_cols, self.output_c_dim)
            opt_t1 = np.float32(scaler_opt_t1.transform(opt_t1))
            opt_t1 = opt_t1.reshape(num_rows, num_cols, self.output_c_dim)
            img_A = np.concatenate((sar_t0, sar_t1, opt_t1), axis=2)
            img_A = img_A.reshape(1, num_rows, num_cols, self.input_c_dim)
            fake_opt = np.zeros((num_rows, num_cols, self.output_c_dim),
                                dtype='float32')
            
            s = 64
            stride = self.image_size-2*s
            for row in range(0, num_rows, stride):
                for col in range(0, num_cols, stride):
                    if (row+self.image_size <= num_rows) and (col+self.image_size <= num_cols):

                        print row + s, row + self.image_size - s
                        sample_image = img_A[:, row:row+self.image_size, col:col+self.image_size]
                        pred = self.sess.run([self.FCN_logits_sample],
                                            feed_dict={self.real_data: sample_image, self.dropout_g: False})
                        sample = np.argmax(pred, axis=2)
                        print sample.shape
                        fake_opt[row+s:row+self.image_size-s, col+s:col+self.image_size-s] = sample[0, s:self.image_size-s, s:self.image_size-s]
                    elif col+self.image_size <= num_cols:
                        sample_image = img_A[:, num_rows-self.image_size:num_rows, col:col+self.image_size]
                        print(sample_image.shape)
                        pred = self.sess.run([self.FCN_logits_sample],
                                            feed_dict={self.real_data: sample_image, self.dropout_g: False})
                        sample = np.argmax(pred, axis=2)
                        print sample.shape
                        fake_opt[row+s:num_rows, col+s:col+self.image_size-s] = sample[0, self.image_size-num_rows+row+s:self.image_size, s:self.image_size-s]
                    elif row+self.image_size <= num_rows:
                        print col
                        sample_image = img_A[:, row:row+self.image_size, num_cols-self.image_size:num_cols]
                        pred = self.sess.run([self.FCN_logits_sample],
                                            feed_dict={self.real_data: sample_image, self.dropout_g: False})
                        sample = np.argmax(pred, axis=2)
                        fake_opt[row+s:row+self.image_size-s, col+s:num_cols] = sample[0, s:self.image_size-s, self.image_size-num_cols+col+s:self.image_size]

            np.save(self.dataset_name + '_classification_map', fake_opt)


    def create_dataset(self, args):
        if '05may2016' in args.dataset_name:
            print 'creating dataset for_' + args.dataset_name
            # sar_img_name = '10_08May_2016.npy'
            # opt_img_name = '20160505/'
            # print sar_img_name, opt_img_name
            # create_dataset_4_classifier(
            #     ksize=256,
            #     dataset=self.dataset_name,
            #     mask_path=None,
            #     sar_path=self.sar_root_patch + sar_img_name,
            #     opt_path=self.opt_root_patch + opt_img_name
            # )
            sar_t0 = '10_08May_2016.npy'
            opt_t0 = '20160505/'
            sar_t1 = '20170520.npy'
            opt_t1 = '20170524/'
            # print sar_img_name, opt_img_name
            # create_dataset_4_classifier_multitemporal(
            #     ksize=256,
            #     dataset=self.dataset_name,
            #     mask_path=None,
            #     sar_path_t0=self.sar_root_patch + sar_t0,
            #     opt_path_t0=self.opt_root_patch + opt_t0,
            #     sar_path_t1=self.sar_root_patch + sar_t1,
            #     opt_path_t1=self.opt_root_patch + opt_t1,
            # )
            # create_dataset_multitemporal_multiresolution_CV(ksize=256,
            #                                                 dataset=self.dataset_name,
            #                                                 mask_path=None,
            #                                                 sar_path_t0=self.sar_root_patch + sar_t0,
            #                                                 opt_path_t0=self.opt_root_patch + opt_t0,
            #                                                 sar_path_t1=self.sar_root_patch + sar_t1,
            #                                                 opt_path_t1=self.opt_root_patch + opt_t1
            #                                                 )
            data_augmentation()
        elif 'quemadas_ap2_case_A' in args.dataset_name:
            print 'creating dataset for_' + args.dataset_name
            create_dataset_case_A(
                ksize=256,
                dataset=self.dataset_name,
                mask_path=None,
                sar_path='/mnt/Data/DataBases/RS/Quemadas/AP2_Acre/Sentinel1/20160909/new_20160909.npy',
                opt_path='/mnt/Data/DataBases/RS/Quemadas/AP2_Acre/Sentinel2/20160825/'
            )
        elif 'quemadas_ap2_case_C' in args.dataset_name:
            print 'creating dataset for_' + args.dataset_name
            create_dataset_case_C(
                ksize=256,
                dataset=self.dataset_name,
                mask_path=None,
                sar_path_t0='/mnt/Data/DataBases/RS/Quemadas/AP2_Acre/Sentinel1/20160909/new_20160909.npy',
                sar_path_t1='/mnt/Data/DataBases/RS/Quemadas/AP2_Acre/Sentinel1/20170731/20170731.npy',
                opt_path_t0='/mnt/Data/DataBases/RS/Quemadas/AP2_Acre/Sentinel2/20160825/',
                opt_path_t1='/mnt/Data/DataBases/RS/Quemadas/AP2_Acre/Sentinel2/20170731/'
            )
        else:
            print "Image pair doesnt exist !!!"
            return 0
        print 'creating dataset for_' + args.dataset_name
