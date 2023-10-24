import os
import time
import torch
import asyncio
import argparse
import bittensor as bt


from typing import List
from targon.protocol import TargonSearchResult
from targon.miner.miner import Miner 
from transformers import AutoModelForCausalLM, AutoTokenizer



class QwenMiner( Miner ):
    def config(self) -> "bt.Config":
        parser = argparse.ArgumentParser(description="Streaming Miner Configs")
        self.add_args(parser)
        return bt.config(parser)

    def add_args(cls, parser: argparse.ArgumentParser):
        """
        Adds custom arguments to the command line parser.

        Developers can introduce additional command-line arguments specific to the miner's
        functionality in this method. These arguments can then be used to configure the miner's operation.

        Args:
            parser (argparse.ArgumentParser):
                The command line argument parser to which custom arguments should be added.
        """
        parser.add_argument(
            "--qwen.do_prompt_injection",
            action="store_true",
            default=False,
            help='Whether to use a custom "system" prompt instead of the one sent by bittensor.',
        )
        parser.add_argument(
            "--qwen.system_prompt",
            type=str,
            help="What prompt to replace the system prompt with",
            default="A chat between a curious user and an artificial intelligence assistant.\nThe assistant gives helpful, detailed, and polite answers to the user's questions. ",
        )

    def __init__(self, *args, **kwargs):
        super(QwenMiner, self).__init__(*args, **kwargs)
        
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen-VL-Chat", trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen-VL-Chat", device_map="cuda", trust_remote_code=True).eval()
        

        bt.logging.info('model loaded, ready to go!')

    def _process_history(self, roles: List[str], messages: List[str]) -> str:
        """
        Processes the conversation history for model input.

        This method takes the roles and messages from the incoming request and constructs
        a conversation history suitable for model input. It also injects a system prompt
        if the configuration specifies to do so.
        """
        processed_history = ""
        if self.config.qwen.do_prompt_injection:
            processed_history += self.config.btlm.system_prompt
        for role, message in zip(roles, messages):
            if role == "system":
                if not self.config.qwen.do_prompt_injection or message != messages[0]:
                    processed_history += "system: " + message + "\n"
            if role == "assistant":
                processed_history += "assistant: " + message + "\n"
            if role == "user":
                processed_history += "user: " + message + "\n"
        return processed_history


    def prompt(self, synapse: TargonSearchResult) -> TargonSearchResult:
        """
        Generates a streaming response for the provided synapse.

        This function serves as the main entry point for handling streaming prompts. It takes
        the incoming synapse which contains messages to be processed and returns a streaming
        response. The function uses the GPT-2 tokenizer and a simulated model to tokenize and decode
        the incoming message, and then sends the response back to the client token by token.

        Args:
            synapse (TargonSearchResultStream): The incoming TargonSearchResultStream instance containing the messages to be processed.

        Returns:
            TargonSearchResultStream: The streaming response object which can be used by other functions to
                            stream back the response to the client.

        Usage:
            This function can be extended and customized based on specific requirements of the
            miner. Developers can swap out the tokenizer, model, or adjust how streaming responses
            are generated to suit their specific applications.
        """

        chat_state = CONV_VISION.copy()
        img_list = []

        if len(synapse.images) > 0:
            #TODO: upload image
            bt.logging.info('images', synapse.images)
            images = []
            for tensor_image in synapse.images:
                image = transforms.ToPILImage()( bt.Tensor.deserialize(tensor_image) )
                self.chat.upload_img(image, chat_state, img_list)

        history = self._process_history(roles=synapse.roles, messages=synapse.messages)
        history += "assistant: "
        bt.logging.debug("History: {}".format(history))

        self.chat.ask(synapse.messages[-1], chat_state)
        

        output, _ = self.chat.answer(
            conv=chat_state,
            img_list=img_list,
            max_new_tokens=1024,
            max_length=2048,
            )
        
        synapse.completion = output
        return synapse



if __name__ == "__main__":
    bt.debug()
    with QwenMiner():
        while True:
            print("running...", time.time())
            time.sleep(1)

# def main():
#     print("Loading models...")

#     t0 = time.time()

#     model = MiniGPT4(
#         vision_model_path="models/eva_vit_g.pth",
#         llama_model="models/vicuna13b_v0/",
#         q_former_model="models/blip2_pretrained_flant5xxl.pth",
#     )

#     ckpt_path = "models/pretrained_minigpt4.pth"

#     print("Load BLIP2-LLM Checkpoint: {}".format(ckpt_path))
#     ckpt = torch.load(ckpt_path, map_location="cpu")
#     model.load_state_dict(ckpt['model'], strict=False)

#     torch.compile(model)

#     vis_processor = Blip2ImageEvalProcessor()

#     chat = Chat(model, vis_processor, device='cuda:0')

#     t1 = time.time()

#     print("Models loaded in {} seconds".format(t1-t0))

#     for i in range(5):
#         print("Loading image...")

#         t0 = time.time()

#         chat_state = CONV_VISION.copy()
#         img_list = []
#         chat.upload_img("icbm_bicycle.png", chat_state, img_list)

#         t1 = time.time()

#         print("Image loaded in {} seconds".format(t1-t0))

#         t0 = time.time()

#         num_beams = 1
#         temperature = 0.01

#         chat.ask("Tell me what you see on the road.", chat_state)

#         # Callback for each word generated by the LLM
#         def callback_function(word):
#             print(word, end='', flush=True)

#         print("Live output: ", end='', flush=True)

#         output_text = chat.answer_async(conv=chat_state,
#                                     img_list=img_list,
#                                     num_beams=num_beams,
#                                     temperature=temperature,
#                                     max_new_tokens=1024,
#                                     max_length=2048,
#                                     text_callback=callback_function)

#         print("")

#         t1 = time.time()

#         print("LLM response: {}".format(output_text))
#         print(chat_state)
#         print("Generated LLM response in {} seconds".format(t1-t0))

# if __name__ == "__main__":
#     main()