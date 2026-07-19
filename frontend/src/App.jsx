import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { 
  FileText, 
  Files, 
  Play, 
  Download, 
  Check, 
  Loader2,
  ChevronDown,
  Settings,
  HelpCircle,
  ClipboardCheck,
  ChevronRight,
  Upload,
  AlertCircle
} from 'lucide-react'

function App() {
  // --- STATE VARIABLES ---
  const [templateFile, setTemplateFile] = useState(null)
  const [rawFiles, setRawFiles] = useState([])
  const [apiKey, setApiKey] = useState('')
  const [llmModel, setLlmModel] = useState('Llama-3.3-70B-Instruct')
  const [visionModel, setVisionModel] = useState('Qwen2.5-VL-7B-Instruct')
  
  const [isRunning, setIsRunning] = useState(false)
  const [agentStatusText, setAgentStatusText] = useState('Sẵn sàng xử lý')
  const [agentStatusType, setAgentStatusType] = useState('idle') // idle, running, success, error
  const [logs, setLogs] = useState([])
  
  const [sessionId, setSessionId] = useState('')
  const [kpiData, setKpiData] = useState({})
  const [remarks, setRemarks] = useState('')
  const [isCompleted, setIsCompleted] = useState(false)
  
  const [isDownloading, setIsDownloading] = useState(false)
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  
  const consoleRef = useRef(null)
  const configRef = useRef(null)

  // Auto-scroll console
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight
    }
  }, [logs])

  // Close popover when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (configRef.current && !configRef.current.contains(event.target)) {
        setIsConfigOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [])

  // --- HANDLERS ---
  const handleTemplateChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setTemplateFile(e.target.files[0])
    }
  }

  const handleRawFilesChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setRawFiles(Array.from(e.target.files))
    }
  }

  const handleRunAgent = async () => {
    if (!templateFile) {
      alert('Vui lòng tải lên tệp Biểu mẫu báo cáo trống (.docx) ở Bước 1!')
      return
    }
    if (rawFiles.length === 0) {
      alert('Vui lòng tải lên ít nhất một tệp Báo cáo thô phòng ban ở Bước 1!')
      return
    }

    // Reset states
    setLogs([])
    setKpiData({})
    setRemarks('')
    setIsCompleted(false)
    setIsRunning(true)
    setAgentStatusText('Đang nạp tệp tin...')
    setAgentStatusType('running')

    const formData = new FormData()
    formData.append('template', templateFile)
    rawFiles.forEach((file) => {
      formData.append('raws', file)
    })
    
    if (apiKey.trim()) {
      formData.append('fpt_api_key', apiKey.trim())
    }

    try {
      setLogs((prev) => [...prev, { type: 'info', message: 'Nạp tệp tin thành công. Đang khởi chạy ReAct Loop...' }])
      
      const response = await fetch('/api/agent/run', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`Lỗi kết nối HTTP: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const rawJson = line.slice(6)
            try {
              const data = JSON.parse(rawJson)
              handleAgentEvent(data)
            } catch (e) {
              console.error('Lỗi parse SSE JSON:', e)
            }
          }
        }
      }
    } catch (err) {
      console.error(err)
      setLogs((prev) => [...prev, { type: 'error', message: `Gặp sự cố lỗi: ${err.message}` }])
      setAgentStatusText('Lỗi thực thi hệ thống')
      setAgentStatusType('error')
      setIsRunning(false)
    }
  }

  const safeLogMessage = (msg) => {
    if (msg === null || msg === undefined) return ''
    if (typeof msg === 'object') {
      try {
        return JSON.stringify(msg, null, 2)
      } catch (e) {
        return String(msg)
      }
    }
    return String(msg)
  }

  const formatKpiValue = (val) => {
    if (val === null || val === undefined) return ''
    if (typeof val === 'object') {
      try {
        return JSON.stringify(val)
      } catch (e) {
        return String(val)
      }
    }
    return String(val)
  }

  const renderSafeText = (value) => {
    if (value === null || value === undefined) return ''
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value)
      } catch (e) {
        console.warn('[DEBUG] renderSafeText failed stringify', value)
        return String(value)
      }
    }
    return value
  }

  const debugLogDataMessage = (label, value) => {
    if (value && typeof value === 'object') {
      console.warn(`[DEBUG] ${label} is object`, value)
    }
  }

  const handleAgentEvent = (data) => {
    debugLogDataMessage('agent event payload', data)
    if (data.status === 'init') {
      setSessionId(data.session_id)
      setLogs((prev) => [...prev, { type: 'info', message: `Tạo phiên làm việc mới thành công (Session ID: ${data.session_id})` }])
    } 
    else if (data.status === 'running') {
      if (data.thought) {
        debugLogDataMessage('thought', data.thought)
        setLogs((prev) => [...prev, { type: 'thought', message: safeLogMessage(data.thought) }])
      }
      if (data.action && data.action !== 'Không rõ') {
        debugLogDataMessage('action_input', data.action_input)
        let friendlyTool = data.action
        if (data.action === 'extract_schema_tool') friendlyTool = 'Quét cấu trúc biểu mẫu trống'
        if (data.action === 'read_and_clean_raw_tool') friendlyTool = 'Bảo mật dữ liệu thô & che giấu PII'
        if (data.action === 'extract_kpis_tool') friendlyTool = 'Trích xuất các biến số liệu KPI'
        if (data.action === 'validate_and_correct_tool') friendlyTool = 'Kiểm chéo công thức & Tự sửa sai'
        if (data.action === 'generate_section_remarks_tool') friendlyTool = 'Viết nhận xét báo cáo đa khối'
        if (data.action === 'render_docx_report_tool') friendlyTool = 'Kết xuất Word hoàn chỉnh'
        
        setLogs((prev) => [...prev, { type: 'action', message: `${friendlyTool} -> Tham số: ${JSON.stringify(data.action_input)}` }])
      }
      if (data.observation) {
        debugLogDataMessage('observation', data.observation)
        setLogs((prev) => [...prev, { type: 'observation', message: safeLogMessage(data.observation) }])
      }
    } 
    else if (data.status === 'completed') {
      setLogs((prev) => [...prev, { type: 'complete', message: 'Tác tử đã hoàn thành toàn bộ mục tiêu! Báo cáo sẵn sàng tải xuống.' }])
      setAgentStatusText('Hoàn thành xử lý')
      setAgentStatusType('success')
      setIsRunning(false)
      setIsCompleted(true)
      
      const ans = data.final_answer
      if (ans) {
        if (ans.kpi_data) setKpiData(ans.kpi_data)
        if (ans.combined_remarks) setRemarks(ans.combined_remarks)
      }
    } 
    else if (data.status === 'error') {
      setLogs((prev) => [...prev, { type: 'error', message: safeLogMessage(data.message) }])
    }
  }

  const handleKpiValueChange = (key, value) => {
    setKpiData((prev) => ({
      ...prev,
      [key]: value === '' ? null : isNaN(value) ? value : Number(value)
    }))
  }

  const handleDownloadReport = async () => {
    if (!sessionId) {
      alert('Không tìm thấy session hợp lệ. Vui lòng chạy lại Bước 2!')
      return
    }

    setIsDownloading(true)
    try {
      const res = await axios.post('/api/agent/render-docx', {
        session_id: sessionId,
        kpi_data: kpiData,
        remarks: remarks
      }, {
        responseType: 'blob'
      })

      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Bao_cao_tong_hop_${sessionId.slice(0, 8)}.docx`)
      document.body.appendChild(link)
      link.click()
      link.remove()

      if (remarks.trim()) {
        const styleForm = new FormData()
        styleForm.append('key', 'phong_cach_nhan_xet')
        styleForm.append('val', remarks.slice(0, 150))
        await axios.post('/api/agent/style', styleForm)
      }

      setLogs((prev) => [...prev, { type: 'info', message: 'Xuất báo cáo Word và tải về thành công!' }])
    } catch (e) {
      console.error(e)
      alert('Lỗi khi kết xuất file báo cáo Word.')
    } finally {
      setIsDownloading(false)
    }
  }

  const getFriendlyKpiName = (key) => {
    let base = key
    if (key.includes('tong_thu_ngan_sach')) base = 'Thu ngân sách nhà nước'
    else if (key.includes('tong_chi_ngan_sach')) base = 'Chi ngân sách địa phương'
    else if (key.includes('dang_ky_khai_sinh')) base = 'Hồ sơ khai sinh'
    else if (key.includes('dang_ky_khai_tu')) base = 'Hồ sơ khai tử'
    else if (key.includes('tam_tru_moi')) base = 'Hồ sơ đăng ký tạm trú'
    else if (key.includes('chung_thuc_chu_ky')) base = 'Hồ sơ chứng thực chữ ký'
    else if (key.includes('vi_pham_an_ninh_trat_tu')) base = 'Số vụ vi phạm ANTT'

    if (key.endsWith('_ky_truoc')) {
      return `${base} (Kỳ trước)`
    } else if (key.endsWith('_ky_bao_cao')) {
      return `${base} (Kỳ báo cáo)`
    }
    return key
  }

  // Determine current active step navigation highlight
  const getStepStatus = (stepNum) => {
    if (stepNum === 1) {
      return (templateFile && rawFiles.length > 0) ? 'completed' : 'active'
    }
    if (stepNum === 2) {
      if (isRunning) return 'active'
      if (isCompleted) return 'completed'
      return 'inactive'
    }
    if (stepNum === 3) {
      return isCompleted ? 'active' : 'inactive'
    }
    return 'inactive'
  }

  return (
    <div className="bg-[#FAF8F0] min-h-screen flex flex-col font-sans text-slate-800 antialiased">
      
      {/* Header chính */}
      <header className="border-b border-[#E4E2D3] bg-white px-6 py-4 shadow-sm">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            <div className="bg-[#0B54A8] p-3 rounded-xl shadow-md text-white flex items-center justify-center">
              <ClipboardCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-[#0B54A8] font-sans">Trợ lý tổng hợp báo cáo</h1>
              <p className="text-xs text-slate-500 font-medium">Hỗ trợ tổng hợp số liệu, kiểm tra nội dung và hoàn thiện báo cáo định kỳ</p>
            </div>
          </div>
          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-600 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Hệ thống sẵn sàng
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 space-y-6">
        
        {/* Title Section */}
        <div className="flex items-end justify-between flex-wrap gap-4 border-b border-[#E4E2D3] pb-4">
          <div>
            <span className="text-[10px] tracking-[0.15em] font-bold text-slate-400 block mb-1">TỔNG HỢP BÁO CÁO ĐỊNH KỲ</span>
            <h2 className="text-2xl font-bold text-slate-900">Hoàn thiện báo cáo qua 3 bước</h2>
            <p className="text-sm text-slate-500 mt-0.5">Tải tài liệu, để AI hỗ trợ phân tích, sau đó kiểm tra trước khi xuất báo cáo.</p>
          </div>
          
          {/* Popover cấu hình */}
          <div className="relative" ref={configRef}>
            <button 
              onClick={() => setIsConfigOpen(!isConfigOpen)}
              className="bg-white border border-[#E4E2D3] hover:bg-slate-50 px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-700 shadow-sm flex items-center gap-2 cursor-pointer transition-all"
            >
              <Settings className="w-4 h-4 text-slate-500" />
              Tùy chọn hệ thống
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {isConfigOpen && (
              <div className="absolute right-0 top-full mt-2 w-80 bg-white border border-[#E4E2D3] rounded-xl shadow-xl p-4 z-50 text-slate-800">
                <h3 className="text-sm font-bold border-b border-slate-200 pb-2 mb-3 text-[#0B54A8]">Cấu hình mô hình AI</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1.5">Mô hình Lập luận chính:</label>
                    <select 
                      value={llmModel} 
                      onChange={(e) => setLlmModel(e.target.value)}
                      className="w-full bg-[#FAF8F0] border border-[#E4E2D3] rounded-lg px-2.5 py-2 text-xs focus:outline-none focus:border-[#0B54A8] font-semibold text-slate-700"
                    >
                      <option value="Llama-3.3-70B-Instruct">Llama-3.3-70B (FPT Factory)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1.5">Mô hình Vision (Ảnh/Scan):</label>
                    <select 
                      value={visionModel} 
                      onChange={(e) => setVisionModel(e.target.value)}
                      className="w-full bg-[#FAF8F0] border border-[#E4E2D3] rounded-lg px-2.5 py-2 text-xs focus:outline-none focus:border-[#0B54A8] font-semibold text-slate-700"
                    >
                      <option value="Qwen2.5-VL-7B-Instruct">Qwen2.5-VL-7B (FPT Factory)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1.5">FPT AI API Key:</label>
                    <input 
                      type="password" 
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Nhập khóa API cá nhân nếu có..." 
                      className="w-full bg-[#FAF8F0] border border-[#E4E2D3] rounded-lg px-2.5 py-2 text-xs focus:outline-none focus:border-[#0B54A8] font-medium text-slate-700"
                    />
                    <p className="text-[10px] text-slate-400 mt-1">Để trống để sử dụng khóa API cấu hình mặc định trên máy chủ.</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Bộ Stepper Progress Navigation */}
        <div className="bg-white border border-[#E4E2D3] rounded-2xl p-4 shadow-sm grid grid-cols-1 md:grid-cols-5 gap-3 items-center justify-center">
          <div className="md:col-span-1 flex items-center justify-center space-x-3 text-center md:text-left py-1">
            <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
              getStepStatus(1) === 'completed' ? 'bg-emerald-100 text-emerald-600 border border-emerald-300' : 'bg-[#0B54A8] text-white'
            }`}>
              {getStepStatus(1) === 'completed' ? <Check className="w-4 h-4" /> : '1'}
            </span>
            <div>
              <p className="text-xs font-bold text-slate-800">Chọn tài liệu</p>
              <p className="text-[10px] text-slate-400 font-medium">Biểu mẫu và báo cáo nguồn</p>
            </div>
          </div>
          
          <div className="hidden md:flex justify-center text-slate-300">
            <ChevronRight className="w-5 h-5" />
          </div>

          <div className="md:col-span-1 flex items-center justify-center space-x-3 text-center md:text-left py-1">
            <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
              getStepStatus(2) === 'completed' ? 'bg-emerald-100 text-emerald-600 border border-emerald-300' :
              getStepStatus(2) === 'active' ? 'bg-[#0B54A8] text-white' : 'bg-slate-100 text-slate-400 border border-slate-200'
            }`}>
              {getStepStatus(2) === 'completed' ? <Check className="w-4 h-4" /> : '2'}
            </span>
            <div>
              <p className={`text-xs font-bold ${getStepStatus(2) !== 'inactive' ? 'text-slate-800' : 'text-slate-400'}`}>Phân tích</p>
              <p className="text-[10px] text-slate-400 font-medium">Trích xuất và kiểm tra số liệu</p>
            </div>
          </div>

          <div className="hidden md:flex justify-center text-slate-300">
            <ChevronRight className="w-5 h-5" />
          </div>

          <div className="md:col-span-1 flex items-center justify-center space-x-3 text-center md:text-left py-1">
            <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
              getStepStatus(3) === 'active' ? 'bg-[#0B54A8] text-white' : 'bg-slate-100 text-slate-400 border border-slate-200'
            }`}>
              3
            </span>
            <div>
              <p className={`text-xs font-bold ${getStepStatus(3) === 'active' ? 'text-slate-800' : 'text-slate-400'}`}>Kiểm tra và xuất</p>
              <p className="text-[10px] text-slate-400 font-medium">Hoàn thiện báo cáo Word</p>
            </div>
          </div>
        </div>

        {/* STEP 1: CHỌN TÀI LIỆU */}
        <section className="bg-white border border-[#E4E2D3] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center space-x-3 mb-2">
            <span className="flex items-center justify-center bg-slate-100 text-slate-600 w-8 h-8 rounded-lg text-sm font-bold">1</span>
            <div>
              <h2 className="text-md font-bold text-slate-900">Chọn tài liệu</h2>
              <p className="text-xs text-slate-400 mt-0.5">Tải lên biểu mẫu cần điền và các báo cáo nguồn của phòng ban.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-4">
            
            {/* Box Tải biểu mẫu */}
            <div className="border-2 border-dashed border-[#CFCDBC] hover:border-[#0B54A8] bg-[#FAF8F0]/30 transition-colors rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer relative min-h-[160px]">
              <input 
                type="file" 
                accept=".docx" 
                onChange={handleTemplateChange}
                className="absolute inset-0 opacity-0 cursor-pointer" 
              />
              <div className={`p-3.5 rounded-xl mb-3 ${templateFile ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-blue-50 text-[#0B54A8] border border-blue-100'}`}>
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="text-xs font-bold text-slate-700">Biểu mẫu báo cáo</h3>
              <p className="text-[10px] text-slate-400 mt-1 max-w-[200px]">Tệp Word (.docx) cần được hoàn thiện</p>
              <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-[#0B54A8] bg-white border border-[#E4E2D3] px-3.5 py-1.5 rounded-lg shadow-sm hover:bg-slate-50">
                <Upload className="w-3.5 h-3.5" />
                {templateFile ? 'Chọn tệp khác' : 'Chọn tệp từ máy tính'}
              </span>
              {templateFile && (
                <p className="text-[10px] text-emerald-600 font-bold mt-2 truncate max-w-[280px]">✔ {templateFile.name}</p>
              )}
            </div>

            {/* Box Tải tài liệu thô */}
            <div className="border-2 border-dashed border-[#CFCDBC] hover:border-[#0B54A8] bg-[#FAF8F0]/30 transition-colors rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer relative min-h-[160px]">
              <input 
                type="file" 
                multiple 
                accept=".docx,.xlsx,.pdf,.png,.jpg,.jpeg" 
                onChange={handleRawFilesChange}
                className="absolute inset-0 opacity-0 cursor-pointer" 
              />
              <div className={`p-3.5 rounded-xl mb-3 ${rawFiles.length > 0 ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-blue-50 text-[#0B54A8] border border-blue-100'}`}>
                <Files className="w-6 h-6" />
              </div>
              <h3 className="text-xs font-bold text-slate-700">Báo cáo của các phòng ban</h3>
              <p className="text-[10px] text-slate-400 mt-1 max-w-[200px]">Hỗ trợ Word, Excel, PDF và ảnh scan</p>
              <span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-[#0B54A8] bg-white border border-[#E4E2D3] px-3.5 py-1.5 rounded-lg shadow-sm hover:bg-slate-50">
                <Upload className="w-3.5 h-3.5" />
                {rawFiles.length > 0 ? 'Chọn tệp khác' : 'Chọn một hoặc nhiều tệp'}
              </span>
              {rawFiles.length > 0 && (
                <p className="text-[10px] text-emerald-600 font-bold mt-2 truncate max-w-[280px]">
                  ✔ Đã nạp {rawFiles.length} tệp tin
                </p>
              )}
            </div>
            
          </div>
        </section>

        {/* STEP 2: PHÂN TÍCH VÀ KIỂM TRA SỐ LIỆU */}
        <section className="bg-white border border-[#E4E2D3] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-100 pb-4 mb-4">
            <div className="flex items-center space-x-3">
              <span className="flex items-center justify-center bg-slate-100 text-slate-600 w-8 h-8 rounded-lg text-sm font-bold">2</span>
              <div>
                <h2 className="text-md font-bold text-slate-900">Phân tích và kiểm tra số liệu</h2>
                <p className="text-xs text-slate-400 mt-0.5">Al sẽ đọc tài liệu, tổng hợp chỉ tiêu và phát hiện nội dung cần kiểm tra.</p>
              </div>
            </div>
            <button 
              onClick={handleRunAgent}
              disabled={isRunning || !templateFile || rawFiles.length === 0}
              className={`font-bold text-xs px-5 py-2.5 rounded-xl shadow-sm transition-all inline-flex items-center gap-2 cursor-pointer ${
                isRunning || !templateFile || rawFiles.length === 0
                  ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed' 
                  : 'bg-[#0B54A8] hover:bg-[#084184] text-white'
              }`}
            >
              {isRunning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              Phân tích báo cáo
            </button>
          </div>

          <div className="bg-[#FAF8F0] border border-[#E4E2D3] rounded-xl overflow-hidden">
            {/* Header Tiến trình */}
            <div className="bg-white border-b border-[#E4E2D3] px-4 py-2.5 flex items-center justify-between text-xs font-bold text-slate-700">
              <span className="flex items-center gap-1.5 text-[#0B54A8]">
                <Loader2 className={`w-4 h-4 ${isRunning ? 'animate-spin text-[#0B54A8]' : 'text-slate-400'}`} />
                Tiến trình xử lý
              </span>
              <span className={`text-xs ${
                agentStatusType === 'success' ? 'text-emerald-600' :
                agentStatusType === 'error' ? 'text-rose-600' :
                agentStatusType === 'running' ? 'text-[#0B54A8] animate-pulse' : 'text-slate-500'
              }`}>{agentStatusText}</span>
            </div>

            {/* Khung log ReAct console */}
            <div 
              ref={consoleRef}
              className="p-4 h-60 overflow-y-auto custom-scrollbar font-mono text-xs space-y-2 bg-[#FAF8F0]"
            >
              {logs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 space-y-2 py-8">
                  <HelpCircle className="w-9 h-9 text-[#CFCDBC]" />
                  <p className="text-xs font-semibold text-slate-500">Chọn đầy đủ tài liệu rồi nhấn Phân tích báo cáo để bắt đầu.</p>
                </div>
              ) : (
                logs.map((log, index) => {
                  let badge = '';
                  let textClass = 'text-slate-600';
                  
                  if (log.type === 'thought') {
                    badge = 'Tác tử lập luận';
                    textClass = 'text-[#0B54A8] italic font-semibold';
                  } else if (log.type === 'action') {
                    badge = 'Gọi công cụ';
                    textClass = 'text-amber-800 font-bold';
                  } else if (log.type === 'observation') {
                    badge = 'Kết quả quan sát';
                    textClass = 'text-slate-500 text-[11px]';
                  } else if (log.type === 'error') {
                    badge = 'Lỗi hệ thống';
                    textClass = 'text-rose-600 font-bold';
                  } else if (log.type === 'complete') {
                    badge = 'Hoàn thành';
                    textClass = 'text-emerald-700 font-bold';
                  }

                  return (
                    <div key={index} className="py-1.5 border-b border-[#E4E2D3]/30 last:border-0">
                      {badge && (
                        <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] uppercase font-bold mr-2 ${
                          log.type === 'thought' ? 'bg-blue-50 text-[#0B54A8] border border-blue-200' :
                          log.type === 'action' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
                          log.type === 'observation' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                          log.type === 'error' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                          'bg-emerald-500 text-white'
                        }`}>
                          {badge}
                        </span>
                      )}
                      <span className={textClass}>{renderSafeText(log.message)}</span>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </section>

        {/* STEP 3: KIỂM TRA VÀ XUẤT BÁO CÁO */}
        <section className="bg-white border border-[#E4E2D3] rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-100 pb-4 mb-4">
            <div className="flex items-center space-x-3">
              <span className="flex items-center justify-center bg-slate-100 text-slate-600 w-8 h-8 rounded-lg text-sm font-bold">3</span>
              <div>
                <h2 className="text-md font-bold text-slate-900">Kiểm tra và xuất báo cáo</h2>
                <p className="text-xs text-slate-400 mt-0.5">Rà soát số liệu và nội dung nhận xét trước khi tải báo cáo.</p>
              </div>
            </div>
            <button 
              onClick={handleDownloadReport}
              disabled={isDownloading || !sessionId || !isCompleted}
              className={`font-bold text-xs px-5 py-2.5 rounded-xl shadow-sm transition-all inline-flex items-center gap-2 cursor-pointer ${
                isDownloading || !sessionId || !isCompleted
                  ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed' 
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white'
              }`}
            >
              {isDownloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              Tải báo cáo Word
            </button>
          </div>

          {!isCompleted ? (
            <div className="bg-[#FAF8F0]/50 border-2 border-dashed border-[#CFCDBC] rounded-xl p-8 text-center flex flex-col items-center justify-center min-h-[220px]">
              <ClipboardCheck className="w-10 h-10 text-[#CFCDBC] mb-2" />
              <p className="text-xs font-semibold text-slate-500">Kết quả sẽ hiển thị tại đây sau khi hệ thống phân tích xong.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-2">
              
              {/* Bảng chỉnh sửa số liệu */}
              <div className="bg-[#FAF8F0] border border-[#E4E2D3] rounded-xl p-4 flex flex-col">
                <h3 className="text-xs font-bold text-[#0B54A8] mb-3 flex items-center gap-1.5 border-b border-[#E4E2D3] pb-2">
                  Chỉ tiêu báo cáo trích xuất
                </h3>
                <div className="space-y-2.5 max-h-[340px] overflow-y-auto custom-scrollbar pr-1.5">
                  {Object.keys(kpiData).length === 0 ? (
                    <p className="text-xs text-slate-500 italic">Không tìm thấy chỉ số chỉ tiêu tương thích.</p>
                  ) : (
                    Object.entries(kpiData).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between gap-4 p-2 bg-white rounded-lg border border-[#E4E2D3]">
                        <label className="text-xs font-bold text-slate-600 w-2/3 truncate" title={key}>
                          {getFriendlyKpiName(key)}
                        </label>
                        <input 
                          type="text" 
                          value={formatKpiValue(val)} 
                          onChange={(e) => handleKpiValueChange(key, e.target.value)}
                          className="w-1/3 bg-[#FAF8F0] border border-[#E4E2D3] rounded px-2.5 py-1 text-right text-xs font-bold text-slate-800 focus:outline-none focus:border-[#0B54A8]"
                        />
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Bảng chỉnh sửa nhận định */}
              <div className="bg-[#FAF8F0] border border-[#E4E2D3] rounded-xl p-4 flex flex-col">
                <h3 className="text-xs font-bold text-[#0B54A8] mb-3 flex items-center gap-1.5 border-b border-[#E4E2D3] pb-2">
                  Đoạn văn nhận định đánh giá (Cán bộ có thể chỉnh sửa)
                </h3>
                <textarea 
                  rows={14} 
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="Đoạn văn nhận định của AI sẽ hiển thị ở đây..."
                  className="w-full bg-white border border-[#E4E2D3] rounded-lg p-3 text-xs text-slate-700 focus:outline-none focus:border-[#0B54A8] font-sans custom-scrollbar flex-1 resize-none font-medium leading-relaxed"
                />
              </div>
              
            </div>
          )}
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-[#E4E2D3] bg-white py-4 text-center text-xs text-slate-400 font-semibold mt-12">
        © 2026 Ủy ban nhân dân cấp phường. Thiết kế React Frontend di trú thông suốt.
      </footer>
    </div>
  )
}

export default App
