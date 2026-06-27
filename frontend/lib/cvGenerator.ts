import { Job } from './types';

interface CVData {
  name: string;
  email: string;
  phone?: string;
  github?: string;
  linkedin?: string;
  website?: string;
  summary?: string;
  education?: string | string[];
  experience?: Array<{ title: string; company: string; description: string }>;
  projects?: Array<{ name: string; skills: string[] }>;
  skills?: string[];
  languages?: string[];
}

interface TailoredCVData {
  summary: string;
  highlighted_skills: string[];
  relevant_projects: Array<{ name: string; why_relevant: string }>;
  tailoring_notes: string;
}

// Sanitize text for safe HTML insertion
function sanitizeHtml(text: string | undefined): string {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Format GitHub URL - handle both username and full URL
function formatGitHubURL(github: string): string {
  if (!github) return '';
  if (github.startsWith('http')) return github;
  if (github.startsWith('github.com')) return `https://${github}`;
  return `https://github.com/${github}`;
}

// Extract GitHub handle from URL or username
function extractGitHubHandle(github: string): string {
  if (!github) return 'GitHub';
  if (github.includes('github.com')) {
    const match = github.match(/github\.com\/([^/]+)/);
    return match ? `github.com/${match[1]}` : 'GitHub';
  }
  return `github.com/${github}`;
}

// Format LinkedIn URL - handle both username and full URL
function formatLinkedInURL(linkedin: string): string {
  if (!linkedin) return '';
  if (linkedin.startsWith('http')) return linkedin;
  if (linkedin.startsWith('linkedin.com')) return `https://${linkedin}`;
  return `https://linkedin.com/in/${linkedin}`;
}

// Extract LinkedIn handle from URL or username
function extractLinkedInHandle(linkedin: string): string {
  if (!linkedin) return 'LinkedIn';
  if (linkedin.includes('linkedin.com')) {
    const match = linkedin.match(/linkedin\.com\/in\/([^/]+)/);
    return match ? `linkedin.com/in/${match[1]}` : 'LinkedIn';
  }
  return `linkedin.com/in/${linkedin}`;
}

export async function generateCVHTML(
  job: Job,
  tailored: TailoredCVData,
  cvData: CVData
): Promise<string> {
  const today = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${sanitizeHtml(cvData.name)} - CV for ${sanitizeHtml(job.title)}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    html, body {
      width: 100%;
      height: 100%;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif;
      line-height: 1.6;
      color: #1f2937;
      background: white;
    }

    @media print {
      body {
        margin: 0;
        padding: 0;
      }
      .cv-container {
        max-width: 100%;
        box-shadow: none;
      }
      page-break-after: avoid;
    }

    .cv-container {
      max-width: 850px;
      margin: 40px auto;
      padding: 40px;
      background: white;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
      font-size: 11pt;
    }

    /* Header */
    .header {
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 2px solid #111827;
    }

    .name {
      font-size: 24pt;
      font-weight: 700;
      letter-spacing: -0.5px;
      margin-bottom: 8px;
      color: #111827;
    }

    .job-title {
      font-size: 14pt;
      color: #6b7280;
      margin-bottom: 12px;
      font-weight: 500;
    }

    .contact-info {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 10pt;
      color: #4b5563;
    }

    .contact-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    /* Section */
    .section {
      margin-bottom: 20px;
    }

    .section-title {
      font-size: 12pt;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: #111827;
      margin-bottom: 10px;
      padding-bottom: 6px;
      border-bottom: 1px solid #d1d5db;
    }

    /* Summary */
    .summary-text {
      font-size: 11pt;
      line-height: 1.5;
      color: #374151;
      text-align: justify;
      margin-bottom: 4px;
    }

    /* Skills */
    .skills-container {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .skill-tag {
      display: inline-block;
      background-color: #f3f4f6;
      border: 1px solid #d1d5db;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 10pt;
      font-weight: 500;
      color: #1f2937;
    }

    /* Projects */
    .project-item {
      margin-bottom: 14px;
      page-break-inside: avoid;
    }

    .project-name {
      font-weight: 700;
      font-size: 11pt;
      color: #111827;
      margin-bottom: 4px;
    }

    .project-description {
      font-size: 10.5pt;
      color: #374151;
      line-height: 1.4;
      margin-left: 0;
    }

    /* Target Job Info */
    .target-job {
      background-color: #f9fafb;
      padding: 12px 16px;
      border-left: 3px solid #111827;
      margin-bottom: 16px;
      font-size: 10pt;
    }

    .target-job-title {
      font-weight: 700;
      color: #111827;
      margin-bottom: 4px;
    }

    .target-job-details {
      display: flex;
      gap: 16px;
      color: #4b5563;
      font-size: 9.5pt;
    }

    /* Footer */
    .footer {
      margin-top: 24px;
      padding-top: 12px;
      border-top: 1px solid #d1d5db;
      font-size: 9pt;
      color: #6b7280;
      text-align: center;
    }

    /* Print styles */
    @media print {
      .cv-container {
        margin: 0;
        padding: 0.5in;
        box-shadow: none;
        max-width: 100%;
      }
      .header {
        page-break-after: avoid;
      }
      .section {
        page-break-inside: avoid;
      }
    }
  </style>
</head>
<body>
  <div class="cv-container">
    <!-- Header -->
    <div class="header">
      <div class="name">${sanitizeHtml(cvData.name)}</div>
      <div class="job-title">${sanitizeHtml(job.title)}</div>
      <div class="contact-info">
        ${cvData.email ? `<div class="contact-item">${sanitizeHtml(cvData.email)}</div>` : ''}
        ${cvData.phone ? `<div class="contact-item">${sanitizeHtml(cvData.phone)}</div>` : ''}
        ${cvData.github ? `<div class="contact-item"><a href="${formatGitHubURL(cvData.github)}" style="color: #4b5563; text-decoration: none;">${extractGitHubHandle(cvData.github)}</a></div>` : ''}
        ${cvData.linkedin ? `<div class="contact-item"><a href="${formatLinkedInURL(cvData.linkedin)}" style="color: #4b5563; text-decoration: none;">${extractLinkedInHandle(cvData.linkedin)}</a></div>` : ''}
        ${cvData.website ? `<div class="contact-item"><a href="${sanitizeHtml(cvData.website)}" style="color: #4b5563; text-decoration: none;">Website</a></div>` : ''}
      </div>
    </div>

    <!-- Target Job Context -->
    <div class="target-job">
      <div class="target-job-title">Position: ${sanitizeHtml(job.title)}</div>
      <div class="target-job-details">
        <span>${sanitizeHtml(job.company)}</span>
        ${job.location ? `<span>${sanitizeHtml(job.location)}</span>` : ''}
        ${job.modality ? `<span>${sanitizeHtml(job.modality)}</span>` : ''}
      </div>
    </div>

    <!-- Professional Summary -->
    <div class="section">
      <div class="section-title">Professional Summary</div>
      <p class="summary-text">${sanitizeHtml(tailored.summary || 'Dedicated professional with strong experience in relevant technologies and problem-solving capabilities.')}</p>
    </div>

    <!-- Core Competencies -->
    ${tailored.highlighted_skills && tailored.highlighted_skills.length > 0 ? `
    <div class="section">
      <div class="section-title">Core Competencies</div>
      <div class="skills-container">
        ${tailored.highlighted_skills.map(skill => `<span class="skill-tag">${sanitizeHtml(skill)}</span>`).join('')}
      </div>
    </div>
    ` : ''}

    <!-- Experience -->
    ${cvData.experience && cvData.experience.length > 0 ? `
    <div class="section">
      <div class="section-title">Professional Experience</div>
      ${cvData.experience.map((exp: any) => `
        <div class="project-item">
          <div class="project-name">${sanitizeHtml(exp.title)} at ${sanitizeHtml(exp.company)}</div>
          ${exp.location ? `<div class="project-description" style="margin-bottom: 4px;">${sanitizeHtml(exp.location)}${exp.dates ? ` | ${sanitizeHtml(exp.dates)}` : ''}</div>` : ''}
          ${exp.description ? `<div class="project-description">${sanitizeHtml(exp.description)}</div>` : ''}
        </div>
      `).join('')}
    </div>
    ` : ''}

    <!-- Relevant Projects -->
    ${tailored.relevant_projects && tailored.relevant_projects.length > 0 ? `
    <div class="section">
      <div class="section-title">Relevant Projects</div>
      ${tailored.relevant_projects.map((project: any) => {
        // Find the project in cvData to get dates and other details
        const projectDetails = cvData.projects?.find((p: any) => p.name === project.name);
        return `
        <div class="project-item">
          <div class="project-name">${sanitizeHtml(project.name)}${projectDetails?.date ? ` | ${sanitizeHtml(projectDetails.date)}` : ''}</div>
          ${projectDetails?.skills && projectDetails.skills.length > 0 ? `<div class="project-description" style="margin-bottom: 4px;"><strong>Skills:</strong> ${projectDetails.skills.map((s: string) => sanitizeHtml(s)).join(', ')}</div>` : ''}
          <div class="project-description">${sanitizeHtml(project.why_relevant)}</div>
        </div>
      `;
      }).join('')}
    </div>
    ` : ''}

    <!-- Education -->
    ${cvData.education ? `
    <div class="section">
      <div class="section-title">Education</div>
      ${typeof cvData.education === 'string' ? `
        <p class="summary-text">${sanitizeHtml(cvData.education)}</p>
      ` : Array.isArray(cvData.education) ? `
        ${cvData.education.map((edu: any) => {
          if (typeof edu === 'string') {
            return `<p class="summary-text">${sanitizeHtml(edu)}</p>`;
          } else {
            return `
            <div class="project-item">
              <div class="project-name">${sanitizeHtml(edu.degree)}${edu.date ? ` | ${sanitizeHtml(edu.date)}` : ''}</div>
              ${edu.institution ? `<div class="project-description">${sanitizeHtml(edu.institution)}${edu.location ? `, ${sanitizeHtml(edu.location)}` : ''}</div>` : ''}
              ${edu.gpa ? `<div class="project-description"><strong>GPA:</strong> ${sanitizeHtml(edu.gpa)}</div>` : ''}
            </div>
            `;
          }
        }).join('')}
      ` : ''}
    </div>
    ` : ''}

    <!-- All Skills (from CV) -->
    ${cvData.skills && cvData.skills.length > 0 ? `
    <div class="section">
      <div class="section-title">Technical Skills</div>
      <div class="skills-container">
        ${cvData.skills.map(skill => `<span class="skill-tag">${sanitizeHtml(skill)}</span>`).join('')}
      </div>
    </div>
    ` : ''}

    <!-- Languages -->
    ${cvData.languages && cvData.languages.length > 0 ? `
    <div class="section">
      <div class="section-title">Languages</div>
      <p class="summary-text">${sanitizeHtml(cvData.languages.join(' • '))}</p>
    </div>
    ` : ''}

    <!-- Footer -->
    <div class="footer">
      <p>Generated on ${today} • Tailored for ${sanitizeHtml(job.title)} position at ${sanitizeHtml(job.company)}</p>
    </div>
  </div>
</body>
</html>`;

  return html;
}

export function downloadCVAsHTML(
  filename: string,
  htmlContent: string
): void {
  const blob = new Blob([htmlContent], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
