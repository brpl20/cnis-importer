const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Configuration
const BASE_URL = 'https://planilha.tramitacaointeligente.com.br';
const LOGIN_EMAIL = 'adv5898@gmail.com';
const LOGIN_PASSWORD = 'Lerdaviva12#';
const CNIS_DIR = path.join(__dirname, 'sensitive-f2');
const DOWNLOAD_DIR = path.join(__dirname, 'downloads');
const SPECS_DIR = path.join(__dirname, 'specs');
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const DEBUG = process.env.DEBUG === '1';

// 30 selected CNIS PDFs (unique people, 2025/2026)
const CNIS_FILES = [
  'ADEMAR FRANCISCO ROMAN (2330) - CNIS - 2025.03.pdf',
  'ADILSON SANTOS (3337) - CNIS 2025.10.pdf',
  'ALICE ALVES RODRIGUES (3316) - CNIS 2025.04.pdf',
  'APARECIDA VIEIRA GOMES PEREIRA (3258) - CNIS 2025.02.pdf',
  'ARLETE MARIA GUSATTO (2783) - 2025-03-CNIS.pdf',
  'CAMILA DO NASCIMENTO DAPIEVE (3256) - CNIS 2025-09.pdf',
  'CELSO RAMOS DA SILVEIRA (3054) - CNIS 2025.11.pdf',
  'CREUSA LEMES ANDRADE LOPES (3266) - CNIS 2025.05.pdf',
  'DAYANE FERREIRA DA SILVA (3227) - CNIS 2025.09.pdf',
  'DEILDO BATISTA CORREA (3246) - CNIS - 2025.01.pdf',
  'DILSON CORREA (3247) - CNIS 2025.04.pdf',
  'DONISETE FRANCISCO PAES (3208) - CNIS 2025.06.pdf',
  'EDEMILSON SEMINI (3303) - CNIS 2025.05.pdf',
  'EDU LOPES (3156) - CNIS 2025.01.pdf',
  'ELIANE KOPCHINSKI (2954) - extrato CNIS 2026.02.pdf',
  'ELIZABETE DOS SANTOS (3191) - CNIS 2026.02.pdf',
  'EMILIENNE SAMPAIO NERYS (3329-2947) - CNIS 2025.07.pdf',
  'ENOR MASSONI (1499) - CNIS 2025.02.pdf',
  'FATIMA APARECIDA REIS DE SOUZA (3151) - CNIS 2025.07.pdf',
  'FERNANDO ROCETO (3282) - CNIS 2026.01.pdf',
  'GILBERTO ALVES PEREIRA (3241) - CNIS 2025.01.pdf',
  'HILDA KASUMI YASSUNAGA SUZUKI (3346) - CNIS 2026.02.pdf',
  'JOANA HARDT LOURENCO (3320) - CNIS 2025.06.pdf',
  'JOAO MAURI FRANCO (2951) - CNIS 2025.01.pdf',
  'JOSE FERREIRA DE ANDRADE (3255) - CNIS 2025.03.pdf',
  'JULIA OLIVEIRA DE SOUZA MENDES (3187) - CNIS - 2025.01.pdf',
  'JULIO CESAR DE SOUZA (2755) - CNIS - 2025.01.pdf',
  'LEANDRO MEDEIROS (3281) - CNIS 2025.09.pdf',
  'LEUZELENA DE ANDRADE (3183) - CNIS 2025.01.pdf',
  'LORENI LIMA MORAES (3150) - CNIS 2025.10.pdf',
  'LOURDES PEREIRA DE SOUZA (3345) - CNIS 2026.03.pdf',
  'LUCIA SANTANA MARQUES MACHADO (3298) - CNIS 2025.07.pdf',
  'LUCIANO PAULO SOARES DO PRADO (3265) - CNIS 2025.04.pdf',
  'MARILDA APARECIDA BONETTI FAZAN (3215) - CNIS 2025.03.pdf',
  'MARLI ALVELINO DE OLIVEIRA (3175) - CNIS 2025.01.pdf',
  'MONICA CRISTINA FERNANDES (3276) - CNIS 2025.06.pdf',
  'NADIR FAVERO (3302) - CNIS 2025.08.pdf',
  'ODAIR JOSÉ DA SILVA MENDES (3295) - CNIS 2025.08.pdf',
  'OSVALDO BELO DA SILVA (3235) - CNIS 2025.04.pdf',
  'ROSALIA WILHELM (3075) - CNIS 2025.09.pdf',
];

// Helpers
function randomBirthDate() {
  const year = 1950 + Math.floor(Math.random() * 40);
  const month = 1 + Math.floor(Math.random() * 12);
  const day = 1 + Math.floor(Math.random() * 28);
  return `${String(day).padStart(2, '0')}/${String(month).padStart(2, '0')}/${year}`;
}

function randomSex() {
  return Math.random() > 0.5 ? 'Masculino' : 'Feminino';
}

function extractName(filename) {
  const match = filename.match(/^(.+?)\s*\(/);
  return match ? match[1].trim() : filename.replace('.pdf', '');
}

function generateTitle(index, name) {
  const randomSuffix = Math.random().toString(36).substring(2, 6).toUpperCase();
  return `TESTE-${String(index + 1).padStart(2, '0')}-${randomSuffix}-${name}`;
}

function safeName(name) {
  return name.replace(/[^a-zA-Z0-9]/g, '_');
}

async function screenshot(page, label) {
  if (!DEBUG) return;
  const filename = `debug_${Date.now()}_${label}.png`;
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, filename), fullPage: true });
  console.log(`  [DEBUG] Screenshot: ${filename}`);
}

// === MAIN FLOW ===

async function login(page) {
  console.log('Logging in...');
  await page.goto(`${BASE_URL}/usuarios/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(2000);

  // Check if we're already logged in (redirected to dashboard)
  if (page.url().includes('/dashboard') || page.url().includes('/planilhas')) {
    console.log('Already logged in!');
    return;
  }

  await screenshot(page, 'login_page');

  // Fill email (id="email", data-test="email")
  await page.fill('input#email[data-test="email"]', LOGIN_EMAIL);

  // Fill password (id="password", data-test="password")
  await page.fill('input#password[data-test="password"]', LOGIN_PASSWORD);

  await screenshot(page, 'login_filled');

  // Click "Entrar" button (data-test="login_btn")
  await page.click('button[data-test="login_btn"]');

  // Wait for navigation after login
  await page.waitForLoadState('networkidle', { timeout: 30000 });
  await page.waitForTimeout(3000);

  console.log('Logged in. URL:', page.url());
  await screenshot(page, 'after_login');
}

async function createPlanilhaCompleta(page) {
  console.log('  Creating new planilha completa...');

  // Navigate directly to create a new complete planilha
  await page.goto(`${BASE_URL}/planilhas/nova/completa`, { waitUntil: 'domcontentloaded', timeout: 30000 });

  // Wait for the planilha form to load (it redirects to the hash URL)
  await page.waitForSelector('input[data-test="dataDeNascimento"]', { timeout: 30000 });
  await page.waitForTimeout(4000);

  const url = page.url();
  console.log('  Planilha created:', url);
  await screenshot(page, 'planilha_created');
  return url;
}

async function fillFormData(page, index, cnisFile) {
  const name = extractName(cnisFile);
  const birthDate = randomBirthDate();
  const sex = randomSex();
  const title = generateTitle(index, name);
  const der = '26/03/2026';

  console.log(`  Filling: birth=${birthDate}, sex=${sex}`);
  console.log(`  Title: ${title}`);

  // Fill birth date
  const birthInput = page.locator('input[data-test="dataDeNascimento"]');
  await birthInput.click();
  await page.waitForTimeout(500);
  await birthInput.fill('');
  await birthInput.type(birthDate, { delay: 80 });
  await page.waitForTimeout(1000);

  // Select sex
  await page.locator('select[data-test="seletor_sexo"]').selectOption(sex);
  await page.waitForTimeout(1000);

  // Fill title
  const titleInput = page.locator('input[data-test="tituloDaPlanilha"]');
  await titleInput.click();
  await page.waitForTimeout(500);
  await titleInput.fill('');
  await titleInput.type(title, { delay: 50 });
  await page.waitForTimeout(1000);

  // Fill DER - try multiple selectors
  // Based on the screenshot, DER is in section 3 "Parâmetros"
  // The button "Preencher com a data de hoje" might be easier
  const derTodayBtn = page.locator('button:has-text("Preencher com a data de hoje")');
  if (await derTodayBtn.count() > 0) {
    await derTodayBtn.click();
    console.log('  DER filled with today\'s date via button.');
  } else {
    // Try filling the DER input directly
    const derInput = page.locator('input[data-tour="der"]');
    if (await derInput.count() > 0) {
      await derInput.click();
      await derInput.fill('');
      await derInput.type(der, { delay: 50 });
    } else {
      // Try placeholder-based selector
      const derByPlaceholder = page.locator('input[placeholder*="Data de Entrada"]');
      if (await derByPlaceholder.count() > 0) {
        await derByPlaceholder.first().click();
        await derByPlaceholder.first().fill('');
        await derByPlaceholder.first().type(der, { delay: 50 });
      }
    }
  }

  await page.waitForTimeout(2000);
  await screenshot(page, 'form_filled');

  return { name, birthDate, sex, title, der };
}

async function uploadCNIS(page, cnisFilePath) {
  const filename = path.basename(cnisFilePath);
  console.log(`  Uploading CNIS: ${filename}`);

  // Click the "Importar um novo CNIS (PDF)" button
  const importBtn = page.locator('button:has-text("Importar um novo CNIS")');
  await importBtn.waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForTimeout(1000);
  await importBtn.click();

  // Wait for modal with file upload to appear
  await page.waitForTimeout(3000);
  await screenshot(page, 'import_modal_open');

  // Find the file input (might be hidden, but Playwright can handle it)
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(cnisFilePath);
  await page.waitForTimeout(2000);

  console.log('  File selected, waiting for processing...');

  // Wait for the CNIS to be processed
  // The system will parse the PDF and populate the fields
  // We need to wait for this to complete - could take 10-30 seconds
  // Watch for indicators: success toast, modal closing, loading spinner disappearing

  // Strategy: wait for network to become idle (upload + processing done)
  // Then check if modal is still open
  let importDone = false;

  // Wait up to 90 seconds for import to finish
  for (let attempt = 0; attempt < 30; attempt++) {
    await page.waitForTimeout(3000);

    // Check if there's a success indicator
    const successText = page.locator('text=importado com sucesso, text=CNIS importado, text=Importação concluída');
    if (await successText.count() > 0) {
      console.log('  CNIS import success indicator found!');
      importDone = true;
      break;
    }

    // Check if modal is still visible
    const modal = page.locator('.modal.show, .modal.in, [class*="modal"][style*="display: block"]');
    if (await modal.count() === 0) {
      console.log('  Modal closed - import likely completed.');
      importDone = true;
      break;
    }

    // Check if there's a loading/processing indicator
    const loading = page.locator('.loading, .spinner, [class*="loading"], [class*="spinner"], .progress-bar');
    if (await loading.count() === 0 && attempt > 3) {
      // No loading indicator and we've waited a bit
      console.log('  No loading indicator found after waiting.');

      // Check for any close/confirm button
      const confirmBtn = page.locator('.modal button:has-text("OK"), .modal button:has-text("Fechar"), .modal button:has-text("Confirmar")');
      if (await confirmBtn.count() > 0) {
        await confirmBtn.first().click();
        await page.waitForTimeout(1000);
        importDone = true;
        break;
      }
    }

    // Check if there's an error
    const errorText = page.locator('.modal .alert-danger, .modal .error, .modal text=erro');
    if (await errorText.count() > 0) {
      const errorMsg = await errorText.first().textContent();
      console.log(`  Import error: ${errorMsg}`);
      // Close the modal and throw
      const closeBtn = page.locator('.modal .close, .modal button:has-text("Fechar")');
      if (await closeBtn.count() > 0) await closeBtn.first().click();
      throw new Error(`CNIS import failed: ${errorMsg}`);
    }

    if (attempt % 5 === 0) {
      console.log(`  Still processing... (${attempt * 3}s elapsed)`);
      await screenshot(page, `import_processing_${attempt}`);
    }
  }

  if (!importDone) {
    await screenshot(page, 'import_timeout');
    // Try to close any remaining modal
    const closeBtn = page.locator('.modal .close, .modal button:has-text("Fechar")');
    if (await closeBtn.count() > 0) {
      await closeBtn.first().click();
      await page.waitForTimeout(1000);
    }
    console.log('  WARNING: Import may not have completed within timeout.');
  }

  await page.waitForTimeout(3000);
  await screenshot(page, 'after_import');
}

async function savePlanilha(page) {
  console.log('  Saving planilha...');

  // Click the Save button directly (first "Salvar" button which is the primary one)
  const saveBtn = page.locator('button:has-text("Salvar")').first();
  if (await saveBtn.count() > 0) {
    await saveBtn.click();
  } else {
    await page.keyboard.press('Meta+s');
  }

  await page.waitForTimeout(5000);

  // Check for "Tudo salvo!" indicator
  const savedIndicator = page.locator('text=Tudo salvo');
  try {
    await savedIndicator.waitFor({ state: 'visible', timeout: 15000 });
    console.log('  Saved successfully!');
  } catch {
    console.log('  Save indicator not found, continuing...');
  }

  // Wait for the page to fully process and render after save
  await page.waitForTimeout(5000);
  await screenshot(page, 'after_save');
}

async function generateAndDownloadPDF(page, outputPath) {
  console.log('  Generating retirement analysis PDF...');

  // Scroll to "Das aposentadorias programáveis" section
  const sectionHeading = page.locator('h3:has-text("aposentadorias")');
  if (await sectionHeading.count() > 0) {
    await sectionHeading.first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
  } else {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(1000);
  }

  await screenshot(page, 'retirement_section');

  // Find the H3 heading "Aposentadoria por tempo de contribuição..." and its nearby "Mostrar" button
  const foundAndClicked = await page.evaluate(() => {
    // Search H3 headings specifically
    const headings = document.querySelectorAll('h3');
    for (const h3 of headings) {
      const text = h3.textContent || '';
      if (text.includes('Aposentadoria por tempo de contribui') && text.includes('por pontos')) {
        // Found the heading - walk up to find the parent panel with a "Mostrar" button
        let parent = h3;
        for (let i = 0; i < 8; i++) {
          parent = parent.parentElement;
          if (!parent) break;
          const buttons = parent.querySelectorAll('button');
          for (const btn of buttons) {
            const btnText = btn.textContent.trim();
            if (btnText === 'Mostrar' || btnText.startsWith('Mostrar')) {
              h3.scrollIntoView({ behavior: 'smooth', block: 'center' });
              btn.click();
              return { found: true, heading: text.trim().substring(0, 80) };
            }
          }
        }
      }
    }
    return { found: false };
  });

  if (foundAndClicked.found) {
    console.log(`  Found and clicked Mostrar for: "${foundAndClicked.heading}"`);
  } else {
    console.log('  WARNING: Could not find section heading. Trying fallback...');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);
  }

  await page.waitForTimeout(7000);
  await screenshot(page, 'retirement_expanded');

  // After clicking Mostrar, the section expands. Find and click "Mostrar análise"
  const clickedAnalise = await page.evaluate(() => {
    const links = document.querySelectorAll('button, a, span');
    for (const link of links) {
      const text = (link.textContent || '').trim();
      // Match: "Mostrar análise da aposentadoria por tempo de contribuição..."
      if (text.startsWith('Mostrar an') && text.includes('tempo de contribui')) {
        link.scrollIntoView({ behavior: 'smooth', block: 'center' });
        link.click();
        return text.substring(0, 80);
      }
    }
    return null;
  });
  if (clickedAnalise) {
    console.log(`  Clicked: "${clickedAnalise}"`);
    await page.waitForTimeout(7000);
  } else {
    console.log('  "Mostrar análise" not found, continuing...');
    await page.waitForTimeout(3000);
  }

  await screenshot(page, 'before_pdf_gen');

  // Find the "Gerar PDF" dropdown button using JS for robustness
  const gerarPdfFound = await page.evaluate(() => {
    const buttons = document.querySelectorAll('button.dropdown-toggle');
    for (const btn of buttons) {
      const text = btn.textContent || '';
      if (text.includes('Gerar PDF') && text.includes('Aposentadoria por tempo')) {
        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return true;
      }
    }
    return false;
  });

  if (!gerarPdfFound) {
    console.log('  WARNING: No PDF generation button found!');
    await screenshot(page, 'no_pdf_button');
    return false;
  }

  console.log('  Found "Gerar PDF da Aposentadoria por tempo" button.');
  await page.waitForTimeout(2000);

  // Click the button to open dropdown via JS
  await page.evaluate(() => {
    const buttons = document.querySelectorAll('button.dropdown-toggle');
    for (const btn of buttons) {
      if ((btn.textContent || '').includes('Gerar PDF') && (btn.textContent || '').includes('Aposentadoria por tempo')) {
        btn.click();
        return;
      }
    }
  });
  await page.waitForTimeout(2000);

  await screenshot(page, 'pdf_dropdown_open');

  // Find the open btn-group and its dropdown items
  const pdfItemCount = await page.evaluate(() => {
    const openGroup = document.querySelector('.btn-group.open');
    if (!openGroup) return 0;
    return openGroup.querySelectorAll('.dropdown-menu li:not(.divider):not(.dropdown-header) a').length;
  });
  console.log(`  PDF dropdown items: ${pdfItemCount}`);

  if (pdfItemCount > 0) {
    // Log items and click the first one via JS
    const itemTexts = await page.evaluate(() => {
      const openGroup = document.querySelector('.btn-group.open');
      if (!openGroup) return [];
      const items = openGroup.querySelectorAll('.dropdown-menu li:not(.divider):not(.dropdown-header) a');
      return Array.from(items).map(a => a.textContent.trim().substring(0, 80));
    });
    itemTexts.forEach((t, i) => console.log(`    Item ${i}: "${t}"`));

    // Click the FIRST item via JavaScript to ensure Vue.js handler fires
    await page.evaluate(() => {
      const openGroup = document.querySelector('.btn-group.open');
      if (openGroup) {
        const items = openGroup.querySelectorAll('.dropdown-menu li:not(.divider):not(.dropdown-header) a');
        if (items.length > 0) items[0].click();
      }
    });
    console.log('  Clicked PDF option (via JS), waiting for modal...');

    // A modal will appear with PDF print target options
    // Wait for modal to get the 'in' class (Bootstrap 3 visibility)
    await page.waitForTimeout(3000);
    const modal = page.locator('.modalPdfOptions.in, .modal.in.modal-vertical-center');
    try {
      await modal.waitFor({ state: 'visible', timeout: 15000 });
    } catch {
      // Try triggering the modal via JS as fallback
      console.log('  Modal not visible, trying JS trigger...');
      await page.evaluate(() => {
        const m = document.querySelector('.modalPdfOptions');
        if (m) {
          // Try jQuery modal show
          if (typeof $ !== 'undefined') $(m).modal('show');
        }
      });
      await page.waitForTimeout(3000);
    }
    console.log('  PDF options modal appeared.');
    await screenshot(page, 'pdf_modal');

    // The modal has a "Gerar PDF para o cliente" button - click it
    // Set up download and popup listeners BEFORE clicking
    const downloadPromise = page.waitForEvent('download', { timeout: 120000 }).catch(() => null);
    const popupPromise = page.context().waitForEvent('page', { timeout: 120000 }).catch(() => null);

    const gerarModalBtn = modal.locator('button:has-text("Gerar PDF")');
    if (await gerarModalBtn.count() > 0) {
      console.log('  Clicking "Gerar PDF para o cliente"...');
      await gerarModalBtn.first().click();
    } else {
      console.log('  WARNING: No "Gerar PDF" button in modal!');
      await screenshot(page, 'no_gerar_in_modal');
      return false;
    }

    console.log('  Waiting for PDF generation (download or popup)...');

    // Race: download vs popup vs timeout
    const result = await Promise.race([
      downloadPromise.then(d => d ? { type: 'download', data: d } : null),
      popupPromise.then(p => p ? { type: 'popup', data: p } : null),
      new Promise(resolve => setTimeout(() => resolve(null), 120000)),
    ]);

    if (result && result.type === 'download') {
      const download = result.data;
      await download.saveAs(outputPath);
      console.log(`  PDF saved via download: ${outputPath}`);
      return true;
    }

    if (result && result.type === 'popup') {
      const newPage = result.data;
      await newPage.waitForLoadState('domcontentloaded', { timeout: 30000 }).catch(() => {});
      await newPage.waitForTimeout(5000);
      const newUrl = newPage.url();
      console.log(`  New tab opened: ${newUrl}`);

      if (newUrl.startsWith('blob:')) {
        try {
          const pdfBuffer = await newPage.evaluate(async (url) => {
            const response = await fetch(url);
            const blob = await response.blob();
            const arrayBuffer = await blob.arrayBuffer();
            return Array.from(new Uint8Array(arrayBuffer));
          }, newUrl);
          fs.writeFileSync(outputPath, Buffer.from(pdfBuffer));
          console.log(`  PDF saved from blob: ${outputPath} (${pdfBuffer.length} bytes)`);
          await newPage.close();
          return true;
        } catch (e) {
          console.log(`  Blob extraction failed: ${e.message}`);
        }
      } else if (newUrl.endsWith('.pdf') || newUrl.includes('/pdf')) {
        try {
          const response = await newPage.context().request.get(newUrl);
          fs.writeFileSync(outputPath, await response.body());
          console.log(`  PDF saved from URL: ${outputPath}`);
          await newPage.close();
          return true;
        } catch (e) {
          console.log(`  URL download failed: ${e.message}`);
        }
      }

      await newPage.screenshot({ path: outputPath.replace('.pdf', '_popup.png') }).catch(() => {});
      await newPage.close();
    }

    console.log('  No download or popup received.');
    await screenshot(page, 'pdf_gen_timeout');
  } else {
    console.log('  No dropdown items found!');
    await screenshot(page, 'no_dropdown_items');
  }

  return false;
}

async function processOneCNIS(page, cnisFile, index) {
  const cnisFilePath = path.join(CNIS_DIR, cnisFile);
  const personName = extractName(cnisFile);
  const safePersonName = safeName(personName);
  const outputPdf = path.join(DOWNLOAD_DIR, `${String(index + 1).padStart(2, '0')}_${safePersonName}_analysis.pdf`);

  console.log(`\n${'='.repeat(60)}`);
  console.log(`[${index + 1}/30] Processing: ${personName}`);
  console.log(`File: ${cnisFile}`);
  console.log('='.repeat(60));

  // Check if already processed
  if (fs.existsSync(outputPdf)) {
    console.log('Already processed, skipping.');
    return { success: true, skipped: true, name: personName, file: cnisFile, output: outputPdf };
  }

  // Verify source file exists
  if (!fs.existsSync(cnisFilePath)) {
    console.log('ERROR: Source CNIS file not found!');
    return { success: false, name: personName, file: cnisFile, error: 'Source file not found' };
  }

  try {
    // Step 1: Create new planilha completa
    const planilhaUrl = await createPlanilhaCompleta(page);

    // Step 2: Fill in form data (birth date, sex, title, DER)
    const formData = await fillFormData(page, index, cnisFile);

    // Step 3: Upload the CNIS PDF
    await uploadCNIS(page, cnisFilePath);

    // Step 3.5: Re-fill sex and verify birth date AFTER import (CNIS may clear these)
    console.log('  Re-filling sex after CNIS import...');
    await page.waitForTimeout(2000);
    const sexSelect = page.locator('select[data-test="seletor_sexo"]');
    await sexSelect.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
    const currentSex = await sexSelect.inputValue();
    if (!currentSex) {
      await sexSelect.selectOption(formData.sex);
      console.log(`  Sex re-filled: ${formData.sex}`);
      await page.waitForTimeout(1000);
    } else {
      console.log(`  Sex already set: ${currentSex}`);
    }

    // Also check birth date
    const birthInput = page.locator('input[data-test="dataDeNascimento"]');
    const currentBirth = await birthInput.inputValue();
    if (!currentBirth) {
      await birthInput.click();
      await birthInput.type(formData.birthDate, { delay: 80 });
      console.log(`  Birth date re-filled: ${formData.birthDate}`);
      await page.waitForTimeout(1000);
    }

    // Step 4: Save the planilha
    await savePlanilha(page);

    // Step 5: Generate and download the retirement analysis PDF
    const pdfGenerated = await generateAndDownloadPDF(page, outputPdf);

    // Save metadata regardless
    const metaPath = path.join(SPECS_DIR, `${String(index + 1).padStart(2, '0')}_${safePersonName}_meta.json`);
    fs.writeFileSync(metaPath, JSON.stringify({
      index: index + 1,
      cnis_file: cnisFile,
      person_name: personName,
      planilha_url: planilhaUrl,
      birth_date: formData.birthDate,
      sex: formData.sex,
      der: formData.der,
      title: formData.title,
      output_pdf: pdfGenerated ? outputPdf : null,
      pdf_generated: pdfGenerated,
      processed_at: new Date().toISOString(),
    }, null, 2));

    return { success: pdfGenerated, name: personName, file: cnisFile, output: pdfGenerated ? outputPdf : null };
  } catch (error) {
    console.error(`ERROR processing ${personName}: ${error.message}`);
    const screenshotPath = path.join(SCREENSHOTS_DIR, `error_${index + 1}_${safePersonName}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    return { success: false, name: personName, file: cnisFile, error: error.message };
  }
}

async function main() {
  // Ensure output directories exist
  [DOWNLOAD_DIR, SPECS_DIR, SCREENSHOTS_DIR].forEach(dir => fs.mkdirSync(dir, { recursive: true }));

  const startIndex = parseInt(process.env.START_INDEX || '0');
  const endIndex = parseInt(process.env.END_INDEX || '30');

  console.log('=== CNIS Automation for Tramitacao Inteligente ===');
  console.log(`Processing files ${startIndex + 1} to ${endIndex}`);
  console.log(`Debug mode: ${DEBUG ? 'ON' : 'OFF'}`);
  console.log(`Total CNIS files available: ${CNIS_FILES.length}`);
  console.log();

  const browser = await chromium.launch({
    headless: false,
    slowMo: 150,
  });

  const context = await browser.newContext({
    acceptDownloads: true,
    viewport: { width: 1400, height: 1000 },
  });

  const page = await context.newPage();
  page.setDefaultTimeout(30000);

  // Log console messages from the page for debugging
  if (DEBUG) {
    page.on('console', msg => console.log(`  [BROWSER] ${msg.type()}: ${msg.text()}`));
  }

  try {
    await login(page);

    const results = [];

    for (let i = startIndex; i < Math.min(endIndex, CNIS_FILES.length); i++) {
      const result = await processOneCNIS(page, CNIS_FILES[i], i);
      results.push(result);
      // Pause between files to let the site breathe
      await page.waitForTimeout(3000);
    }

    // Print summary
    console.log('\n\n' + '='.repeat(60));
    console.log('SUMMARY');
    console.log('='.repeat(60));
    const successes = results.filter(r => r.success);
    const skipped = results.filter(r => r.skipped);
    const failures = results.filter(r => !r.success);
    console.log(`Total processed: ${results.length}`);
    console.log(`Successful: ${successes.length} (${skipped.length} skipped)`);
    console.log(`Failed: ${failures.length}`);

    if (failures.length > 0) {
      console.log('\nFailed:');
      failures.forEach(f => console.log(`  - ${f.name}: ${f.error || 'unknown'}`));
    }

    // Save results
    fs.writeFileSync(
      path.join(SPECS_DIR, 'automation_results.json'),
      JSON.stringify({ results, summary: { total: results.length, success: successes.length, failed: failures.length } }, null, 2)
    );
    console.log(`\nResults saved to ${path.join(SPECS_DIR, 'automation_results.json')}`);

  } catch (error) {
    console.error('FATAL ERROR:', error);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'fatal_error.png'), fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }
}

main().catch(console.error);
