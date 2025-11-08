# Deployment Guide for Annakut Project

This is a static website project that can be deployed to various platforms. Follow the instructions below for your preferred hosting service.

## Prerequisites

1. **Git Repository**: Initialize a git repository if you haven't already:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **GitHub Account**: Create a GitHub account if you don't have one.

## Deployment Options

### Option 1: Netlify (Recommended - Easiest)

1. **Create a GitHub Repository**:
   - Go to [GitHub](https://github.com) and create a new repository
   - Push your code:
     ```bash
     git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
     git branch -M main
     git push -u origin main
     ```

2. **Deploy to Netlify**:
   - Go to [Netlify](https://www.netlify.com) and sign up/login
   - Click "Add new site" → "Import an existing project"
   - Connect your GitHub account and select your repository
   - Netlify will automatically detect the settings:
     - **Build command**: Leave empty (or use: `echo 'No build step'`)
     - **Publish directory**: `.` (root directory)
   - Click "Deploy site"
   - Your site will be live at `https://your-site-name.netlify.app`

3. **Custom Domain** (Optional):
   - In Netlify dashboard, go to "Domain settings"
   - Click "Add custom domain" and follow the instructions

### Option 2: Vercel

1. **Push to GitHub** (same as Step 1 above)

2. **Deploy to Vercel**:
   - Go to [Vercel](https://vercel.com) and sign up/login
   - Click "Add New Project"
   - Import your GitHub repository
   - Vercel will auto-detect settings (no build command needed)
   - Click "Deploy"
   - Your site will be live at `https://your-site-name.vercel.app`

### Option 3: GitHub Pages

1. **Push to GitHub** (same as Step 1 above)

2. **Enable GitHub Pages**:
   - Go to your repository on GitHub
   - Click "Settings" → "Pages"
   - Under "Source", select "Deploy from a branch"
   - Choose "main" branch and "/ (root)" folder
   - Click "Save"
   - Your site will be live at `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME`

### Option 4: Cloudflare Pages

1. **Push to GitHub** (same as Step 1 above)

2. **Deploy to Cloudflare Pages**:
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Navigate to "Pages" → "Create a project"
   - Connect your GitHub account and select your repository
   - Build settings:
     - **Framework preset**: None
     - **Build command**: Leave empty
     - **Build output directory**: `.`
   - Click "Save and Deploy"
   - Your site will be live at `https://your-project.pages.dev`

## Important Notes

### Missing Files

Your `index.html` references some files that may need to be added:
- `Annakut 2025 3D.compressed.glb` - 3D model file
- `poster.webp` - Poster image for the 3D model
- `modal-data.json` - Modal content data (referenced in comments)

Make sure these files are in your project directory before deploying.

### File Size Considerations

- 3D model files (`.glb`) can be large. Ensure they're optimized.
- If files are too large, consider:
  - Using a CDN for large assets
  - Compressing files further
  - Using lazy loading

### Testing Before Deployment

1. Test locally by opening `index.html` in a browser
2. Or use a local server:
   ```bash
   # Python 3
   python3 -m http.server 8000
   
   # Node.js (if you have it)
   npx serve .
   ```
3. Visit `http://localhost:8000` in your browser

## Quick Start Commands

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push -u origin main
```

## Troubleshooting

- **3D model not loading**: Check that the `.glb` file path is correct and the file exists
- **Images not showing**: Verify image paths in the `images/` folder
- **Modal not working**: Ensure `modal-data.json` exists and is properly formatted
- **CORS errors**: Some hosting platforms may require specific CORS headers (already configured in netlify.toml)

## Need Help?

If you encounter issues:
1. Check browser console for errors
2. Verify all file paths are correct
3. Ensure all referenced files exist in the project
4. Check hosting platform logs for deployment errors

