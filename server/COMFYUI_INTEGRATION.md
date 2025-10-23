# ComfyUI Integration Setup

This application now integrates with ComfyUI to generate images and videos using custom workflows.

## Prerequisites

1. **ComfyUI Installation**: You need to have ComfyUI installed and running on your system
2. **ComfyUI Server**: The ComfyUI server should be running on `http://127.0.0.1:8188` (default) or your custom URL

## Setup Instructions

### 1. Install ComfyUI
- Download ComfyUI from the official repository
- Install it following the official instructions
- Make sure ComfyUI is working by accessing the web interface

### 2. Configure the Application
1. Go to **Settings** in the application
2. Set the **ComfyUI Server URL** (default: `http://127.0.0.1:8188`)
3. Optionally configure the ComfyUI folder path for local installations

### 3. Using Workflow Files
1. **Export your ComfyUI workflow as JSON using the "API" format** (not the "Original" format)
   - In ComfyUI, go to the menu and select "Save (API Format)" or "Export (API Format)"
   - This format is optimized for programmatic execution
2. Upload the workflow file in any of the generation pages:
   - **Text to Image**: Upload workflow + enter prompt
   - **Text to Video**: Upload workflow + enter prompt  
   - **Image to Video**: Upload workflow + upload image

### 4. Workflow Requirements
Your ComfyUI workflow should:
- Be exported as JSON format using the **"API" format** (preferred over "Original" format)
- Have proper input nodes for text prompts (for text-to-image/video)
- Have proper image input nodes (for image-to-video)
- Output images/videos in a format the application can handle
- The API format includes additional metadata that makes programmatic execution more reliable

## API Endpoints

The backend provides these new endpoints:

- `POST /generate_image` - Generate images from text prompts
- `POST /generate_video` - Generate videos from text prompts
- `POST /generate_image_to_video` - Generate videos from images

## Troubleshooting

### Common Issues:
1. **"Failed to generate" error**: Check if ComfyUI server is running
2. **"Connection refused"**: Verify the ComfyUI server URL in settings
3. **"Invalid workflow"**: Ensure your workflow JSON is valid and exported using the "API" format
4. **"No images generated"**: Check if your workflow has proper output nodes
5. **"Original format detected"**: The app will warn if you upload an Original format workflow - consider re-exporting as API format

### Workflow Format Differences:
- **API Format**: Contains a `workflow` property with the actual workflow data, optimized for programmatic execution
- **Original Format**: Direct workflow structure, may work but API format is preferred for better compatibility

### Debug Steps:
1. Test ComfyUI directly in its web interface
2. Check the ComfyUI server logs for errors
3. Verify the workflow works in ComfyUI before using it in this app
4. Check the backend server logs for detailed error messages

## Technical Details

- The application uses WebSocket connections to monitor ComfyUI execution progress
- Workflows are dynamically modified to inject user prompts and inputs
- Generated files are saved to the `server/outputs` directory
- The application handles both image and video generation workflows
