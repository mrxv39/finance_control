/**
 * CSV Import Module
 * Handles file upload, preview, category adjustment, and import
 */

const ImportCSV = {
  // State
  parsedData: [],
  selectedFile: null,

  /**
   * Initialize the CSV import UI
   */
  init() {
    const container = document.getElementById('import-container');
    if (!container) return;

    container.innerHTML = `
      <div class="import-csv-wrapper">
        <h2>Importar Transacciones CSV</h2>
        
        <div class="upload-section">
          <label for="csv-file-input" class="file-label">
            Seleccionar archivo CSV
          </label>
          <input type="file" id="csv-file-input" accept=".csv" />
          <div id="file-info" class="file-info"></div>
        </div>

        <div id="preview-section" class="preview-section" style="display: none;">
          <h3>Vista Previa</h3>
          <p class="preview-info">
            <span id="preview-count">0</span> transacciones encontradas
          </p>
          <div class="table-wrapper">
            <table id="preview-table" class="preview-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Concepto</th>
                  <th>Importe</th>
                  <th>Categoría</th>
                  <th>Subcategoría</th>
                </tr>
              </thead>
              <tbody id="preview-tbody"></tbody>
            </table>
          </div>
          
          <div class="import-actions">
            <button id="btn-import" class="btn-primary">
              Importar Transacciones
            </button>
            <button id="btn-cancel" class="btn-secondary">
              Cancelar
            </button>
          </div>
        </div>

        <div id="result-section" class="result-section" style="display: none;">
          <div id="result-message" class="result-message"></div>
        </div>
      </div>
    `;

    this.attachEventListeners();
  },

  /**
   * Attach event listeners
   */
  attachEventListeners() {
    const fileInput = document.getElementById('csv-file-input');
    const btnImport = document.getElementById('btn-import');
    const btnCancel = document.getElementById('btn-cancel');

    if (fileInput) {
      fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
    }

    if (btnImport) {
      btnImport.addEventListener('click', () => this.importTransactions());
    }

    if (btnCancel) {
      btnCancel.addEventListener('click', () => this.resetUI());
    }
  },

  /**
   * Handle file selection
   */
  async handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    this.selectedFile = file;
    
    const fileInfo = document.getElementById('file-info');
    fileInfo.textContent = `Archivo: ${file.name} (${this.formatFileSize(file.size)})`;

    try {
      const content = await this.readFileContent(file);
      this.parsedData = this.parseCSV(content);
      
      if (this.parsedData.length === 0) {
        this.showError('No se encontraron transacciones válidas en el archivo CSV');
        return;
      }

      await this.enrichWithSuggestions();
      this.showPreview();
    } catch (error) {
      this.showError(`Error al leer el archivo: ${error.message}`);
    }
  },

  /**
   * Read file content as text
   */
  readFileContent(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = (e) => reject(new Error('Error al leer el archivo'));
      reader.readAsText(file);
    });
  },

  /**
   * Parse CSV content
   */
  parseCSV(content) {
    const lines = content.split('\n').filter(line => line.trim());
    if (lines.length < 2) return [];

    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    
    // Find column indices (flexible column names)
    const dateIdx = this.findColumnIndex(headers, ['date', 'fecha', 'fecha_transaccion', 'transaction_date']);
    const descIdx = this.findColumnIndex(headers, ['description', 'descripcion', 'concepto', 'concept', 'memo', 'nota']);
    const amountIdx = this.findColumnIndex(headers, ['amount', 'importe', 'monto', 'cantidad', 'value']);

    if (dateIdx === -1 || descIdx === -1 || amountIdx === -1) {
      throw new Error('CSV debe tener columnas: fecha, concepto/descripción, e importe');
    }

    const transactions = [];
    
    for (let i = 1; i < lines.length; i++) {
      const values = this.parseCSVLine(lines[i]);
      
      if (values.length <= Math.max(dateIdx, descIdx, amountIdx)) continue;
      
      const fecha = values[dateIdx]?.trim();
      const concepto = values[descIdx]?.trim();
      const importeStr = values[amountIdx]?.trim();
      
      if (!fecha || !concepto || !importeStr) continue;

      try {
        const fechaNorm = this.parseDate(fecha);
        const importe = parseFloat(importeStr.replace(',', '.').replace(/\s/g, ''));
        
        if (fechaNorm && !isNaN(importe)) {
          transactions.push({
            fecha: fechaNorm,
            concepto: concepto,
            importe: importe,
            categoria: '',
            subconcepto: ''
          });
        }
      } catch (e) {
        // Skip invalid row
      }
    }

    return transactions;
  },

  /**
   * Parse a CSV line handling quoted fields
   */
  parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        result.push(current);
        current = '';
      } else {
        current += char;
      }
    }
    result.push(current);
    
    return result.map(v => v.trim().replace(/^"|"$/g, ''));
  },

  /**
   * Find column index by multiple possible names
   */
  findColumnIndex(headers, candidates) {
    for (const candidate of candidates) {
      const idx = headers.indexOf(candidate);
      if (idx !== -1) return idx;
    }
    return -1;
  },

  /**
   * Parse date string to YYYY-MM-DD
   */
  parseDate(dateStr) {
    // Try ISO format first
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      return dateStr;
    }
    
    // Try DD/MM/YYYY
    const match1 = dateStr.match(/^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})$/);
    if (match1) {
      const day = match1[1].padStart(2, '0');
      const month = match1[2].padStart(2, '0');
      const year = match1[3];
      return `${year}-${month}-${day}`;
    }
    
    // Try YYYY/MM/DD
    const match2 = dateStr.match(/^(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})$/);
    if (match2) {
      const year = match2[1];
      const month = match2[2].padStart(2, '0');
      const day = match2[3].padStart(2, '0');
      return `${year}-${month}-${day}`;
    }
    
    return null;
  },

  /**
   * Enrich transactions with category suggestions
   */
  async enrichWithSuggestions() {
    for (const tx of this.parsedData) {
      try {
        const response = await fetch(`/api/sugerir?nota=${encodeURIComponent(tx.concepto)}`);
        if (response.ok) {
          const data = await response.json();
          if (data.sugerencia) {
            tx.categoria = data.sugerencia.categoria || '';
            tx.subconcepto = data.sugerencia.concepto || '';
          }
        }
      } catch (e) {
        // Continue without suggestion
      }
    }
  },

  /**
   * Show preview table
   */
  showPreview() {
    const previewSection = document.getElementById('preview-section');
    const tbody = document.getElementById('preview-tbody');
    const countSpan = document.getElementById('preview-count');

    countSpan.textContent = this.parsedData.length;
    tbody.innerHTML = '';

    this.parsedData.forEach((tx, idx) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${tx.fecha}</td>
        <td>${this.escapeHtml(tx.concepto)}</td>
        <td class="${tx.importe < 0 ? 'negative' : 'positive'}">
          ${this.formatAmount(tx.importe)}
        </td>
        <td>
          <input type="text" 
                 class="edit-categoria" 
                 data-idx="${idx}" 
                 value="${this.escapeHtml(tx.categoria)}" 
                 placeholder="Sin categoría" />
        </td>
        <td>
          <input type="text" 
                 class="edit-subconcepto" 
                 data-idx="${idx}" 
                 value="${this.escapeHtml(tx.subconcepto)}" 
                 placeholder="Sin subcategoría" />
        </td>
      `;
      tbody.appendChild(row);
    });

    // Attach edit listeners
    tbody.querySelectorAll('.edit-categoria').forEach(input => {
      input.addEventListener('change', (e) => {
        const idx = parseInt(e.target.dataset.idx);
        this.parsedData[idx].categoria = e.target.value;
      });
    });

    tbody.querySelectorAll('.edit-subconcepto').forEach(input => {
      input.addEventListener('change', (e) => {
        const idx = parseInt(e.target.dataset.idx);
        this.parsedData[idx].subconcepto = e.target.value;
      });
    });

    previewSection.style.display = 'block';
  },

  /**
   * Import transactions to backend
   */
  async importTransactions() {
    if (!this.selectedFile) return;

    const btnImport = document.getElementById('btn-import');
    btnImport.disabled = true;
    btnImport.textContent = 'Importando...';

    try {
      const formData = new FormData();
      formData.append('file', this.selectedFile);

      const response = await fetch('/api/import/csv', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.ok) {
        this.showSuccess(
          `Importación completada: ${result.imported} importadas, ` +
          `${result.duplicates} duplicadas, ${result.skipped} omitidas`
        );
        
        // Refresh gastos list if available
        if (window.GastosUI && window.GastosUI.loadGastos) {
          setTimeout(() => window.GastosUI.loadGastos(), 1000);
        }
      } else {
        this.showError(result.error || 'Error en la importación');
      }
    } catch (error) {
      this.showError(`Error de red: ${error.message}`);
    } finally {
      btnImport.disabled = false;
      btnImport.textContent = 'Importar Transacciones';
    }
  },

  /**
   * Show success message
   */
  showSuccess(message) {
    const resultSection = document.getElementById('result-section');
    const resultMessage = document.getElementById('result-message');
    
    resultMessage.className = 'result-message success';
    resultMessage.textContent = message;
    resultSection.style.display = 'block';

    document.getElementById('preview-section').style.display = 'none';
  },

  /**
   * Show error message
   */
  showError(message) {
    const resultSection = document.getElementById('result-section');
    const resultMessage = document.getElementById('result-message');
    
    resultMessage.className = 'result-message error';
    resultMessage.textContent = message;
    resultSection.style.display = 'block';
  },

  /**
   * Reset UI
   */
  resetUI() {
    document.getElementById('csv-file-input').value = '';
    document.getElementById('file-info').textContent = '';
    document.getElementById('preview-section').style.display = 'none';
    document.getElementById('result-section').style.display = 'none';
    
    this.parsedData = [];
    this.selectedFile = null;
  },

  /**
   * Utility: Format file size
   */
  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  },

  /**
   * Utility: Format amount
   */
  formatAmount(amount) {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  },

  /**
   * Utility: Escape HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
};

// Auto-initialize if DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => ImportCSV.init());
} else {
  ImportCSV.init();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ImportCSV;
}
