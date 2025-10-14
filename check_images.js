// Quick check script - paste this in browser console at localhost:3000/article/69

// Log all image elements and their src attributes
const imageGallery = document.querySelector('[class*="grid"]');
if (imageGallery) {
    const images = imageGallery.querySelectorAll('img');
    console.log(`Found ${images.length} images in gallery`);
    images.forEach((img, i) => {
        console.log(`Image ${i + 1}:`);
        console.log(`  src: ${img.src}`);
        console.log(`  naturalWidth: ${img.naturalWidth}`);
        console.log(`  naturalHeight: ${img.naturalHeight}`);
        console.log(`  complete: ${img.complete}`);

        // Try to load image and see what happens
        if (img.complete && img.naturalWidth === 0) {
            console.log(`  ❌ Image failed to load`);
        } else if (img.complete) {
            console.log(`  ✓ Image loaded successfully`);
        } else {
            console.log(`  ⏳ Image still loading...`);
        }
    });
}

// Also check what data is in the article
console.log('\n--- Checking article data from React state ---');
// Try to find React fiber node
const root = document.getElementById('__next');
if (root && root._reactRootContainer) {
    console.log('React root found, but can\'t easily access state');
}
console.log('\nOpen Network tab and reload page to see if image requests are failing');
