# Pitch Controllable DDSP Vocoders

<https://github.com/magenta/ddsp>

<https://github.com/YatingMusic/ddsp-singing-vocoders>

In order to achieve high-quality and stable singing voice synthesis, compared with the above repositories, this repository has applied many algorithm improvements, including but not limited to volume augmentation, random-scaled STFT loss, UV regularization and phase prediction.

There are currently two models in the repository , "Sins" is a classic additive synthesis model based on sine wave excitation, and "CombSub" is a new subtractive synthesis model proposed by me, which is based on combtooth wave excitation. The "Sins" model changes the formant when a pitch shift is applied, while the "CombSub" model does not. In other words, the "CombSub" model does not change the timbre of the vocal.

To Use the DDSP vocoders in [DiffSinger (OpenVPI version)](https://github.com/openvpi/DiffSinger), see [DiffSinger.md](https://github.com/yxlllc/pc-ddsp/blob/master/DiffSinger.md).

UPDATE (2023.6.7): Now both the 'CombSub' model and the 'Sins' model have been upgraded, and they better sound quality when doing copy-synthesising (including application in SVS system) and pitch-shifting, so the old version is not compatible.

UPDATE (2023.10.15): Improve the phase filter, so the old version is not compatible.

UPDATE (2024.5.4): Improve the model and refactor the code, so the old version is not compatible.

## 1. Installing the dependencies

We recommend first installing PyTorch from the [official website](https://pytorch.org/), then run:

```bash
pip install -r requirements.txt
```

UPDATE: python 3.8 (windows) + cuda 11.8 + torch 2.0.0 + torchaudio 2.0.1 works, and training is faster.

## 2. Preprocessing

Put all the training dataset (.wav format audio clips) in the below directory: `data/train/raw`. Put all the validation dataset (.wav format audio clips) in the below directory: `data/val/raw`. Then run

```bash
python preprocess.py -c configs/combsub.yaml
```

for a model of combtooth substractive synthesiser, or run

```bash
python preprocess.py -c configs/sins.yaml
```

for a model of sinusoids additive synthesiser.

You can modify the configuration file `config/<model_name>.yaml` before preprocessing. The default configuration is suitable for training 44.1khz high sampling rate vocoder with GTX-1660 graphics card.

NOTE 1: Please keep the sampling rate of all audio clips consistent with the sampling rate in the yaml configuration file ! If it is not consistent, the program can be executed safely, but the resampling during the training process will be very slow.

NOTE 2: The total number of the audio clips for training dataset is recommended to be about 1000, especially long audio clip can be cut into short segments, which will speed up the training, but the duration of all audio clips should not be less than 2 seconds. If there are too many audio clips, you need a large internal-memory or set the 'cache_all_data' option to false in the configuration file.

NOTE 3: The total number of the audio clips for validation dataset is recommended to be about 10, please don't put too many or it will be very slow to do the validation.

## 3. Training

```bash
# train a combsub model as an example
python train.py -c configs/combsub.yaml
```

The command line for training other models is similar.

You can safely interrupt training, then running the same command line will resume training.

You can also finetune the model if you interrupt training first, then re-preprocess the new dataset or change the training parameters (batchsize, lr etc.) and then run the same command line.

## 4. Visualization

```bash
# check the training status using tensorboard
tensorboard --logdir=exp
```

## 5. Copy-synthesising or pitch-shifting test

```bash
# Copy-synthesising test
# wav -> mel, f0 -> wav
python main.py -i <input.wav> -m <model_file.pt> -o <output.wav>
```

```bash
# Pitch-shifting test
# wav -> mel, f0 -> mel (unchaned), f0 (shifted) -> wav
python main.py -i <input.wav> -m <model_file.pt> -o <output.wav> -k <keychange (semitones)>
```

## 6. Some suggestions for the model choice

It is recommended to try the "CombSub" model first, which generally has a low random-scaled STFT loss and relatively good quality when applying a pitch shift.

However, this loss sometimes cannot reflect the subjective sense of hearing.

If the "CombSub" model does not work well, it is recommended to switch to the "Sins" model.

The "Sins" model works also well when applying copy synthesis, but it changes the formant when applying a pitch shift, which changes the timbre.

## 7. Comments on the sound quality

The sound quality of a well-trained DDSP vocoder (seen speaker) will be better than that of the world vocoder or griffin-lim vocoder, and it can also compete with the generative model-based vocoders (such as HifiGAN) when the total amount of training data is relatively small. But for a large amount of training data, the upper limit of sound quality will be lower than that of generative model based vocoders.

Compared with high quality live recordings, the main defect of the current DDSP vocoder is the metallic noise, which may be due to the distortion of phase prediction based on a non-generative model, and the STFT loss overemphasizes the periodic components in the signal, resulting in too many high frequency band harmonics.
