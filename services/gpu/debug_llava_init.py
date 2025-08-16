"""Deep debug of LLaVA initialization to fix image processing"""

import torch
from transformers import AutoTokenizer, BitsAndBytesConfig
from llava.model import LlavaMistralForCausalLM
from llava.mm_utils import get_model_name_from_path, tokenizer_image_token, process_images
from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
from llava.conversation import conv_templates
import sys

print("=" * 80)
print("LLAVA DEEP DEBUG - FIXING IMAGE PROCESSING")
print("=" * 80)

model_name = "liuhaotian/llava-v1.6-mistral-7b"
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"\n1. CUDA Status: {torch.cuda.is_available()}")
print(f"   Device: {device}")
print(f"   PyTorch: {torch.__version__}")

# Load model with 4-bit quantization
print(f"\n2. Loading model: {model_name}")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

try:
    model = LlavaMistralForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    print("   [OK] Model loaded")
except Exception as e:
    print(f"   [FAIL] Model load error: {e}")
    sys.exit(1)

# Check model structure
print("\n3. Model structure analysis:")
print(f"   Model type: {type(model)}")
print(f"   Has get_vision_tower: {hasattr(model, 'get_vision_tower')}")
print(f"   Has get_model: {hasattr(model, 'get_model')}")

# Try to get vision tower
print("\n4. Vision tower initialization:")
vision_tower = model.get_vision_tower()
print(f"   Vision tower (initial): {vision_tower}")

if vision_tower is None:
    print("   Vision tower is None, trying to initialize...")
    
    # Check what the model expects
    if hasattr(model, 'get_model'):
        inner_model = model.get_model()
        print(f"   Inner model type: {type(inner_model)}")
        print(f"   Has vision_tower attr: {hasattr(inner_model, 'vision_tower')}")
        print(f"   Has initialize_vision_modules: {hasattr(inner_model, 'initialize_vision_modules')}")
        
        # Check config
        if hasattr(model, 'config'):
            print(f"\n5. Model config:")
            config = model.config
            print(f"   mm_vision_tower: {getattr(config, 'mm_vision_tower', 'NOT SET')}")
            print(f"   mm_hidden_size: {getattr(config, 'mm_hidden_size', 'NOT SET')}")
            print(f"   mm_vision_select_layer: {getattr(config, 'mm_vision_select_layer', 'NOT SET')}")
            print(f"   mm_vision_select_feature: {getattr(config, 'mm_vision_select_feature', 'NOT SET')}")
            
            # Try manual initialization with config values
            if hasattr(inner_model, 'initialize_vision_modules'):
                print("\n6. Attempting manual vision tower initialization...")
                
                class ModelArgs:
                    def __init__(self):
                        self.vision_tower = getattr(config, 'mm_vision_tower', 'openai/clip-vit-large-patch14-336')
                        self.mm_vision_select_layer = getattr(config, 'mm_vision_select_layer', -2)
                        self.mm_vision_select_feature = getattr(config, 'mm_vision_select_feature', 'patch')
                        self.pretrain_mm_mlp_adapter = getattr(config, 'mm_projector', None)
                        self.tune_mm_mlp_adapter = False
                        self.freeze_mm_mlp_adapter = False
                        self.mm_projector_type = getattr(config, 'mm_projector_type', 'linear')
                        self.mm_use_im_start_end = getattr(config, 'mm_use_im_start_end', False)
                        self.mm_use_im_patch_token = getattr(config, 'mm_use_im_patch_token', True)
                
                model_args = ModelArgs()
                print(f"   Vision tower path: {model_args.vision_tower}")
                
                try:
                    inner_model.initialize_vision_modules(
                        model_args=model_args,
                        fsdp=None
                    )
                    print("   [OK] Vision modules initialized")
                    
                    # Check again
                    vision_tower = model.get_vision_tower()
                    print(f"   Vision tower (after init): {vision_tower}")
                    
                except Exception as e:
                    print(f"   [FAIL] Initialize error: {e}")
                    import traceback
                    traceback.print_exc()

# Check if vision tower has what we need
print("\n7. Vision tower capabilities:")
if vision_tower is not None:
    print(f"   Type: {type(vision_tower)}")
    print(f"   Has image_processor: {hasattr(vision_tower, 'image_processor')}")
    
    if hasattr(vision_tower, 'image_processor'):
        processor = vision_tower.image_processor
        print(f"   Processor type: {type(processor)}")
        print(f"   Processor config: {processor}")
    else:
        print("   No image_processor attribute!")
        
        # Try to access it differently
        if hasattr(vision_tower, 'vision_tower'):
            inner_tower = vision_tower.vision_tower
            print(f"   Inner tower type: {type(inner_tower)}")
            
        # Check for config
        if hasattr(vision_tower, 'config'):
            print(f"   Vision config: {vision_tower.config}")
else:
    print("   Vision tower is still None!")

# Try alternative: Load CLIP processor directly
print("\n8. Alternative: Direct CLIP processor loading")
try:
    from transformers import CLIPImageProcessor
    
    # Try different CLIP models
    clip_models = [
        "openai/clip-vit-large-patch14-336",
        "openai/clip-vit-large-patch14",
        model_name  # Try from the LLaVA model itself
    ]
    
    for clip_model in clip_models:
        try:
            print(f"   Trying: {clip_model}")
            image_processor = CLIPImageProcessor.from_pretrained(clip_model)
            print(f"   [OK] Loaded from {clip_model}")
            print(f"   Processor: {image_processor}")
            break
        except Exception as e:
            print(f"   [FAIL] {e}")
            
except Exception as e:
    print(f"   [FAIL] Could not load CLIP processor: {e}")

# Test the process_images function
print("\n9. Testing process_images function:")
from PIL import Image
import io

# Create test image
test_img = Image.new('RGB', (336, 336), color='blue')

if 'image_processor' in locals():
    try:
        # Test process_images
        from llava.mm_utils import process_images
        
        processed = process_images([test_img], image_processor, model.config)
        print(f"   [OK] Processed shape: {processed.shape}")
        print(f"   Device: {processed.device}")
        print(f"   Dtype: {processed.dtype}")
    except Exception as e:
        print(f"   [FAIL] process_images error: {e}")
        import traceback
        traceback.print_exc()

# Check conversation templates
print("\n10. Conversation templates:")
print(f"   Available: {list(conv_templates.keys())}")
conv_mode = "mistral_instruct"
if conv_mode in conv_templates:
    conv = conv_templates[conv_mode].copy()
    print(f"   Using: {conv_mode}")
    print(f"   Roles: {conv.roles}")
    print(f"   Sep style: {conv.sep_style}")

print("\n" + "=" * 80)
print("DEBUG COMPLETE - Analyzing results...")
print("=" * 80)