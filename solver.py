import time

import numpy as np
import torch

from logger import utils
from logger.saver import Saver


def test(args, model, loss_func, loader_test, saver):
    print(" [*] testing...")
    model.eval()

    # intialization
    num_batches = len(loader_test)
    rtf_all = []
    test_loss_dict = {}

    # run
    with torch.no_grad():
        for bidx, data in enumerate(loader_test):
            fn = data["name"][0]
            print("--------")
            print("{}/{} - {}".format(bidx, num_batches, fn))

            # unpack data
            for k in data.keys():
                if k != "name":
                    data[k] = data[k].to(args.device).float()
            print(">>", data["name"][0])

            # forward
            st_time = time.time()
            signal, _, (s_h, s_n) = model(data["mel"], data["f0"])
            ed_time = time.time()

            # crop
            min_len = np.min([signal.shape[1], data["audio"].shape[1]])
            signal = signal[:, :min_len]
            data["audio"] = data["audio"][:, :min_len]

            # RTF
            run_time = ed_time - st_time
            song_time = data["audio"].shape[-1] / args.data.sampling_rate
            rtf = run_time / song_time
            print("RTF: {}  | {} / {}".format(rtf, run_time, song_time))
            rtf_all.append(rtf)

            # loss
            loss, loss_dict = loss_func(
                signal, s_h, data["audio"], data["uv"], prefix="validation/"
            )

            if test_loss_dict == {}:
                for key, value in loss_dict.items():
                    test_loss_dict[key] = value / num_batches
            else:
                for key, value in loss_dict.items():
                    test_loss_dict[key] += value / num_batches

            # log
            saver.log_audio({fn + "/gt.wav": data["audio"], fn + "/pred.wav": signal})

    # report
    print(" [test_loss] test_loss:", test_loss_dict["validation/loss"])
    print(" [test_loss] test_loss_rss:", test_loss_dict["validation/loss_rss"])
    print(" Real Time Factor", np.mean(rtf_all))
    return test_loss_dict


def train(
    args, initial_global_step, model, optimizer, loss_func, loader_train, loader_test
):
    # saver
    saver = Saver(args, initial_global_step=initial_global_step)

    # model size
    params_count = utils.get_network_paras_amount({"model": model})
    saver.log_info("--- model size ---")
    saver.log_info(params_count)

    # run
    best_loss = np.inf
    num_batches = len(loader_train)
    model.train()
    saver.log_info("======= start training =======")
    for epoch in range(args.train.epochs):
        for batch_idx, data in enumerate(loader_train):
            saver.global_step_increment()
            optimizer.zero_grad()

            # unpack data
            for k in data.keys():
                if k != "name":
                    data[k] = data[k].to(args.device)

            # forward
            signal, _, (s_h, s_n) = model(data["mel"], data["f0"], infer=False)

            # loss
            detach_uv = False
            if saver.global_step < args.loss.detach_uv_step:
                detach_uv = True
            loss, loss_dict = loss_func(
                signal,
                s_h,
                data["audio"],
                data["uv"],
                detach_uv=detach_uv,
                uv_tolerance=args.loss.uv_tolerance,
                prefix="train/",
            )

            # handle nan loss
            if torch.isnan(loss):
                raise ValueError(" [x] nan loss ")
            else:
                # backpropagate
                loss.backward()
                optimizer.step()

            # log loss
            if saver.global_step % args.train.interval_log == 0:
                saver.log_info(
                    "epoch: {} | {:3d}/{:3d} | {} | batch/s: {:.2f} | loss: {:.3f} | rss: {:.3f} | time: {} | step: {}".format(
                        epoch,
                        batch_idx,
                        num_batches,
                        args.env.expdir,
                        args.train.interval_log / saver.get_interval_time(),
                        loss_dict["train/loss"],
                        loss_dict["train/loss_rss"],
                        saver.get_total_time(),
                        saver.global_step,
                    )
                )
                saver.log_value(loss_dict)

            # validation
            if saver.global_step % args.train.interval_val == 0:
                optimizer_save = optimizer if args.train.save_opt else None

                # save latest
                saver.save_model(model, optimizer_save, postfix=f"{saver.global_step}")

                # run testing set
                test_loss_dict = test(args, model, loss_func, loader_test, saver)

                saver.log_info(
                    " --- <validation> --- \nloss: {:.3f} | rss: {:.3f}. ".format(
                        test_loss_dict["validation/loss"],
                        test_loss_dict["validation/loss_rss"],
                    )
                )
                saver.log_value(test_loss_dict)
                model.train()
