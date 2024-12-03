import argparse

import torch

from data_loaders import get_data_loaders
from ddsp.loss import HybridLoss
from ddsp.vocoder import CombSub, Sins
from logger import utils
from solver import train


def parse_args(args=None, namespace=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", type=str, required=True, help="path to the config file"
    )
    return parser.parse_args(args=args, namespace=namespace)


if __name__ == "__main__":
    # parse commands
    cmd = parse_args()

    # load config
    args = utils.load_config(cmd.config)
    print(" > config:", cmd.config)
    print(" >    exp:", args.env.expdir)

    # load model
    model = None

    if args.model.type == "Sins":
        model = Sins(
            sampling_rate=args.data.sampling_rate,
            block_size=args.data.block_size,
            win_length=args.model.win_length,
            use_mean_filter=args.model.use_mean_filter,
            n_harmonics=args.model.n_harmonics,
            n_mag_noise=args.model.n_mag_noise,
            n_mels=args.data.n_mels,
        )

    elif args.model.type == "CombSub":
        model = CombSub(
            sampling_rate=args.data.sampling_rate,
            block_size=args.data.block_size,
            win_length=args.model.win_length,
            use_mean_filter=args.model.use_mean_filter,
            n_mag_harmonic=args.model.n_mag_harmonic,
            n_mag_noise=args.model.n_mag_noise,
            n_mels=args.data.n_mels,
        )

    else:
        raise ValueError(f" [x] Unknown Model: {args.model.type}")

    # load parameters
    optimizer = torch.optim.AdamW(model.parameters())
    initial_global_step, model, optimizer = utils.load_model(
        args.env.expdir, model, optimizer, device=args.device
    )
    for param_group in optimizer.param_groups:
        param_group["lr"] = args.train.lr
        param_group["weight_decay"] = args.train.weight_decay

    # loss
    loss_func = HybridLoss(
        args.data.block_size,
        args.loss.fft_min,
        args.loss.fft_max,
        args.loss.n_scale,
        args.loss.lambda_uv,
        args.device,
    )

    # device
    if args.device == "cuda":
        torch.cuda.set_device(args.env.gpu_id)
    model.to(args.device)

    for state in optimizer.state.values():
        for k, v in state.items():
            if torch.is_tensor(v):
                state[k] = v.to(args.device)

    loss_func.to(args.device)

    # datas
    loader_train, loader_valid = get_data_loaders(args, whole_audio=False)

    # run
    train(
        args,
        initial_global_step,
        model,
        optimizer,
        loss_func,
        loader_train,
        loader_valid,
    )
