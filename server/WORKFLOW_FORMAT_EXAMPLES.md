# ComfyUI Workflow Format Examples

## API Format (Recommended)

The API format is the preferred format for programmatic execution. It has this structure:

```json
{
  "prompt": {
    "1": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": "a beautiful landscape",
        "clip": ["2", 0]
      }
    },
    "2": {
      "class_type": "CLIPLoader",
      "inputs": {
        "clip_name": "clip_l.safetensors"
      }
    },
    "3": {
      "class_type": "CheckpointLoaderSimple",
      "inputs": {
        "ckpt_name": "v1-5-pruned-emaonly.ckpt"
      }
    }
  }
}
```

**Note**: Some API formats may also use a `workflow` property instead of `prompt`, but `prompt` is the standard ComfyUI API format.

## Original Format (Legacy)

The original format has a direct structure:

```json
{
  "1": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "a beautiful landscape",
      "clip": ["2", 0]
    }
  },
  "2": {
    "class_type": "CLIPLoader",
    "inputs": {
      "clip_name": "clip_l.safetensors"
    }
  }
}
```

## Key Differences

1. **API Format**:
   - Contains a `prompt` property with the actual workflow data (standard)
   - May also contain a `workflow` property in some variants
   - Optimized for programmatic execution
   - Better error handling and validation

2. **Original Format**:
   - Direct workflow structure
   - No additional metadata
   - May work but less reliable for API usage
   - Legacy format

## How to Export API Format

1. Open ComfyUI
2. Load your workflow
3. Go to the menu (hamburger icon)
4. Select "Save (API Format)" or "Export (API Format)"
5. Save the JSON file

## Application Support

Our application:
- **Prefers** API format workflows
- **Supports** both formats for backward compatibility
- **Warns** when Original format is detected
- **Recommends** re-exporting as API format for best results

