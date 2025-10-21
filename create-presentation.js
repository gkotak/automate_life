const pptxgen = require('pptxgenjs');
const html2pptx = require('./.claude/skills/document-skills/pptx/scripts/html2pptx');

async function createPresentation() {
    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9';
    pptx.author = 'Gaurav Kotak';
    pptx.title = 'Automate Life - AI-Powered Content Processing';
    pptx.subject = 'Personal knowledge management system';

    // Slide 1: Title
    await html2pptx('slide1-title.html', pptx);

    // Slide 2: Problem
    await html2pptx('slide2-problem.html', pptx);

    // Slide 3: Solution
    await html2pptx('slide3-solution.html', pptx);

    // Slide 4: Architecture
    await html2pptx('slide4-architecture.html', pptx);

    // Slide 5: Workflow
    await html2pptx('slide5-workflow.html', pptx);

    // Slide 6: Features
    await html2pptx('slide6-features.html', pptx);

    // Slide 7: Tech Stack
    await html2pptx('slide7-tech.html', pptx);

    // Slide 8: Results
    await html2pptx('slide8-results.html', pptx);

    // Slide 9: Future
    await html2pptx('slide9-future.html', pptx);

    // Slide 10: Closing
    await html2pptx('slide10-closing.html', pptx);

    // Save
    await pptx.writeFile({ fileName: 'Automate_Life_Presentation.pptx' });
    console.log('Presentation created successfully: Automate_Life_Presentation.pptx');
}

createPresentation().catch(console.error);
