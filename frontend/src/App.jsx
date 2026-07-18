import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { 
  ShieldAlert, 
  Settings2, 
  HelpCircle, 
  FileText, 
  Files, 
  Play, 
  Terminal, 
  Download, 
  Table, 
  Edit3, 
  Loader2,
  CheckCircle,
  AlertTriangle,
  ChevronDown
} from 'lucide-react'

function App() {
  // --- STATE VARIABLES ---
  const [templateFile, setTemplateFile] = useState(null)
  const [rawFiles, setRawFiles] = useState([])
  const [apiKey, setApiKey] = useState('')
  const [llmModel, setLlmModel] = useState('Llama-3.3-70B-Instruct')
  const [visionModel, setVisionModel] = useState('Qwen2.5-VL-7B-Instruct')
  
  const [isRunning, setIsRunning] = useState(false)
  const [agentStatusText, setAgentStatusText] = useState('Chờ lệnh khởi chạy...')
  const [agentStatusType, setAgentStatusType] = useState('idle') // idle, running, success, error
  const [logs, setLogs] = useState([])
  
  const [sessionId, setSessionId] = useState('')
  const [kpiData, setKpiData] = useState({})
  const [remarks, setRemarks] = useState('')
  const [isCompleted, setIsCompleted] = useState(false)
  
  const [isDownloading, setIsDownloading] = useState(false)
  
  const consoleRef = useRef(null)

  // Tự động cuộn console xuống khi có log mới
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight
    }
  }, [logs])

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

  // Khởi chạy Agentic Loop qua Server-Sent Events (SSE)
  const handleRunAgent = async () => {
    if (!templateFile) {
      alert('Vui lòng tải lên tệp Biểu mẫu báo cáo trống (.docx) ở Bước 1!')
      return
    }
    if (rawFiles.length === 0) {
      alert('Vui lòng tải lên ít nhất một tệp Báo cáo thô phòng ban ở Bước 1!')
      return
    }

    // Reset các trạng thái
    setLogs([])
    setKpiData({})
    setRemarks('')
    setIsCompleted(false)
    setIsRunning(true)
    setAgentStatusText('🤖 Đang kết nối server và nạp tệp...')
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
        // Giữ lại phần chưa hoàn thành
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
      setAgentStatusText('❌ Lỗi thực thi hệ thống')
      setAgentStatusType('error')
      setIsRunning(false)
    }
  }

  // Điều phối sự kiện SSE từ backend
  const handleAgentEvent = (data) => {
    if (data.status === 'init') {
      setSessionId(data.session_id)
      setLogs((prev) => [...prev, { type: 'info', message: `Tạo phiên làm việc mới thành công (Session ID: ${data.session_id})` }])
    } 
    else if (data.status === 'running') {
      if (data.thought) {
        setLogs((prev) => [...prev, { type: 'thought', message: data.thought }])
      }
      if (data.action && data.action !== 'Không rõ') {
        // Bình dân hóa tên công cụ tiếng Việt
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
        setLogs((prev) => [...prev, { type: 'observation', message: data.observation }])
      }
    } 
    else if (data.status === 'completed') {
      setLogs((prev) => [...prev, { type: 'complete', message: 'Tác tử đã hoàn thành toàn bộ mục tiêu! Báo cáo sẵn sàng tải xuống.' }])
      setAgentStatusText('✅ Hoàn thành thành công')
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
      setLogs((prev) => [...prev, { type: 'error', message: data.message }])
      setAgentStatusText('❌ Lỗi trong ReAct Loop')
      setAgentStatusType('error')
      setIsRunning(false)
    }
  }

  // Cập nhật giá trị KPI cụ thể khi cán bộ thay đổi thủ công trên form
  const handleKpiValueChange = (key, value) => {
    setKpiData((prev) => ({
      ...prev,
      [key]: value === '' ? null : isNaN(value) ? value : Number(value)
    }))
  }

  // Tải báo cáo Word hoàn chỉnh về máy khách (Human-in-the-loop)
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
        responseType: 'blob' // Nhận file nhị phân
      })

      // Tạo URL download file Word
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Bao_cao_tong_hop_${sessionId.slice(0, 8)}.docx`)
      document.body.appendChild(link)
      link.click()
      link.remove()

      // Lưu phong cách thói quen văn phong mẫu
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

  // Lấy nhãn chỉ tiêu tiếng Việt rõ ràng
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

  return (
    <div className="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
      
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-indigo-600 p-2.5 rounded-xl shadow-lg shadow-indigo-500/20 text-white">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white font-sans">VAIC AI Report Agent</h1>
            <p className="text-xs text-indigo-400 font-medium">Hệ thống Trợ lý Tác tử AI Phân tích & Tự động điền báo cáo</p>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Tác tử Sẵn sàng Kết nối
          </span>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 p-6 max-w-7xl mx-auto w-full">
        
        <aside className="lg:col-span-1 flex flex-col space-y-5">
          <div className="glass-panel rounded-2xl p-5 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2 border-b border-slate-700 pb-2">
              <Settings2 className="w-5 h-5 text-indigo-400" />
              Cấu hình mô hình AI
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-1.5">Mô hình Lập luận chính:</label>
                <div className="relative">
                  <select 
                    value={llmModel} 
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 appearance-none"
                  >
                    <option value="Llama-3.3-70B-Instruct">Llama-3.3-70B (FPT Factory)</option>
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-3 pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-1.5">Mô hình Vision (Ảnh/Scan):</label>
                <div className="relative">
                  <select 
                    value={visionModel} 
                    onChange={(e) => setVisionModel(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 appearance-none"
                  >
                    <option value="Qwen2.5-VL-7B-Instruct">Qwen2.5-VL-7B (FPT Factory)</option>
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-3 pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-1.5">FPT AI API Key:</label>
                <input 
                  type="password" 
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Nhập khóa API nếu có..." 
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">Hệ thống sẽ tự động sử dụng khóa API cấu hình sẵn nếu bỏ trống.</p>
              </div>
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-5 shadow-xl bg-indigo-950/20 border-indigo-500/10">
            <h3 className="text-sm font-bold text-indigo-400 mb-2.5 flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4" />
              Hướng dẫn nhanh
            </h3>
            <ul className="space-y-2 text-xs text-slate-300 list-decimal pl-4">
              <li>Nạp tệp tin biểu mẫu trống (.docx) ở Bước 1.</li>
              <li>Nạp một hoặc nhiều tệp báo cáo thô của phòng ban.</li>
              <li>Bấm nút "Khởi chạy" ở Bước 2 và quan sát AI tư duy.</li>
              <li>Duyệt lại số liệu/nhận xét và bấm "Tải về" ở Bước 3.</li>
            </ul>
          </div>
        </aside>

        <main className="lg:col-span-3 flex flex-col space-y-6">
          
          <section className="glass-panel rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span className="flex items-center justify-center bg-indigo-600/30 text-indigo-400 w-7 h-7 rounded-lg text-sm font-bold">1</span>
              Bước 1: Tải lên Biểu mẫu & Báo cáo thô phòng ban
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border-2 border-dashed border-slate-700 hover:border-indigo-500 transition-colors rounded-2xl p-5 flex flex-col items-center justify-center text-center cursor-pointer relative bg-slate-900/50">
                <input 
                  type="file" 
                  accept=".docx" 
                  onChange={handleTemplateChange}
                  className="absolute inset-0 opacity-0 cursor-pointer" 
                />
                <div className={`p-3 rounded-xl mb-3 ${templateFile ? 'bg-emerald-500/10 text-emerald-400' : 'bg-indigo-600/10 text-indigo-400'}`}>
                  <FileText className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-bold text-slate-200">
                  {templateFile ? 'Đã chọn biểu mẫu trống:' : 'Biểu mẫu báo cáo trống (.docx)'}
                </h3>
                <p className={`text-xs mt-1 ${templateFile ? 'text-emerald-400 font-semibold' : 'text-slate-400'}`}>
                  {templateFile ? templateFile.name : 'Kéo thả tệp hoặc bấm để chọn tệp tin'}
                </p>
              </div>

              <div className="border-2 border-dashed border-slate-700 hover:border-indigo-500 transition-colors rounded-2xl p-5 flex flex-col items-center justify-center text-center cursor-pointer relative bg-slate-900/50">
                <input 
                  type="file" 
                  multiple 
                  accept=".docx,.xlsx,.pdf,.png,.jpg,.jpeg" 
                  onChange={handleRawFilesChange}
                  className="absolute inset-0 opacity-0 cursor-pointer" 
                />
                <div className={`p-3 rounded-xl mb-3 ${rawFiles.length > 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-indigo-600/10 text-indigo-400'}`}>
                  <Files className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-bold text-slate-200">
                  {rawFiles.length > 0 ? `Đã nạp ${rawFiles.length} tài liệu thô:` : 'Tài liệu thô phòng ban (Nhiều tệp)'}
                </h3>
                <p className={`text-xs mt-1 truncate max-w-xs ${rawFiles.length > 0 ? 'text-emerald-400 font-semibold' : 'text-slate-400'}`}>
                  {rawFiles.length > 0 ? rawFiles.map(f => f.name).join(', ') : 'Hỗ trợ Excel, Word, PDF, Ảnh báo cáo...'}
                </p>
              </div>
            </div>
          </section>

          <section className="glass-panel rounded-2xl p-6 shadow-xl">
            <div className="text-lg font-bold text-white mb-4 flex items-center justify-between flex-wrap gap-3">
              <span className="flex items-center gap-2">
                <span className="flex items-center justify-center bg-indigo-600/30 text-indigo-400 w-7 h-7 rounded-lg text-sm font-bold">2</span>
                Bước 2: AI tự động phân tích & Kiểm lỗi logic chéo
              </span>
              <button 
                onClick={handleRunAgent}
                disabled={isRunning}
                className={`font-bold text-sm px-6 py-2.5 rounded-xl shadow-lg transition-all inline-flex items-center gap-2 ${
                  isRunning 
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed' 
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/25'
                }`}
              >
                {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Khởi chạy Tác tử AI
              </button>
            </div>

            <div className="bg-slate-950 rounded-xl border border-slate-800 p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800 pb-2 mb-3">
                <span className="font-semibold flex items-center gap-1.5">
                  <Terminal className="w-4 h-4 text-indigo-400" />
                  Nhật ký tư duy của Tác tử AI (ReAct Loop)
                </span>
                <span className={`font-semibold ${
                  agentStatusType === 'success' ? 'text-emerald-400' :
                  agentStatusType === 'error' ? 'text-rose-400' :
                  agentStatusType === 'running' ? 'text-indigo-400 animate-pulse' : 'text-slate-500'
                }`}>{agentStatusText}</span>
              </div>

              <div 
                ref={consoleRef}
                className="h-64 overflow-y-auto custom-scrollbar font-mono text-xs space-y-3 pr-2"
              >
                {logs.length === 0 ? (
                  <div className="text-slate-500 italic">Vui lòng tải lên tệp tin và bấm nút "Khởi chạy Tác tử AI" để bắt đầu...</div>
                ) : (
                  logs.map((log, index) => {
                    let badge = '';
                    let textClass = 'text-slate-300';
                    
                    if (log.type === 'thought') {
                      badge = 'Tác tử lập luận';
                      textClass = 'text-indigo-200 italic font-semibold';
                    } else if (log.type === 'action') {
                      badge = 'Gọi công cụ';
                      textClass = 'text-amber-200 font-bold';
                    } else if (log.type === 'observation') {
                      badge = 'Kết quả quan sát';
                      textClass = 'text-slate-400 text-[11px]';
                    } else if (log.type === 'error') {
                      badge = 'Lỗi hệ thống';
                      textClass = 'text-rose-400 font-bold';
                    } else if (log.type === 'complete') {
                      badge = 'Hoàn thành';
                      textClass = 'text-emerald-400 font-bold';
                    }

                    return (
                      <div key={index} className="py-1 border-b border-slate-900/50 last:border-0">
                        {badge && (
                          <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] uppercase font-bold mr-1.5 ${
                            log.type === 'thought' ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/20' :
                            log.type === 'action' ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20' :
                            log.type === 'observation' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            log.type === 'error' ? 'bg-rose-500/15 text-rose-400 border border-rose-500/20' :
                            'bg-emerald-500 text-slate-950'
                          }`}>
                            {badge}
                          </span>
                        )}
                        <span className={textClass}>{log.message}</span>
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          </section>

          <section className={`glass-panel rounded-2xl p-6 shadow-xl transition-all duration-300 ${
            isCompleted ? 'opacity-100' : 'opacity-50 pointer-events-none'
          }`}>
            <div className="text-lg font-bold text-white mb-5 flex items-center justify-between flex-wrap gap-3">
              <span className="flex items-center gap-2">
                <span className="flex items-center justify-center bg-indigo-600/30 text-indigo-400 w-7 h-7 rounded-lg text-sm font-bold">3</span>
                Bước 3: Hiệu chỉnh số liệu & Tải báo cáo Word hoàn chỉnh
              </span>
              <button 
                onClick={handleDownloadReport}
                disabled={isDownloading || !sessionId}
                className={`font-bold text-sm px-6 py-2.5 rounded-xl shadow-lg transition-all inline-flex items-center gap-2 ${
                  isDownloading || !sessionId
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed' 
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/25'
                }`}
              >
                {isDownloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Tải báo cáo Word (.docx)
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex flex-col">
                <h3 className="text-sm font-bold text-indigo-400 mb-3 flex items-center gap-1.5">
                  <Table className="w-4 h-4" />
                  Số liệu trích xuất chỉ tiêu báo cáo
                </h3>
                <div className="space-y-3 max-h-80 overflow-y-auto custom-scrollbar pr-1 flex-1">
                  {Object.keys(kpiData).length === 0 ? (
                    <p className="text-xs text-slate-500 italic">Chưa có số liệu trích xuất...</p>
                  ) : (
                    Object.entries(kpiData).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between gap-4 p-2 bg-slate-950/40 rounded-lg border border-slate-800/60">
                        <label className="text-xs font-semibold text-slate-300 w-2/3 truncate" title={key}>
                          {getFriendlyKpiName(key)}
                        </label>
                        <input 
                          type="text" 
                          value={val !== null ? val : ''} 
                          onChange={(e) => handleKpiValueChange(key, e.target.value)}
                          className="w-1/3 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                        />
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 flex flex-col">
                <h3 className="text-sm font-bold text-indigo-400 mb-3 flex items-center gap-1.5">
                  <Edit3 className="w-4 h-4" />
                  Đoạn văn nhận xét đánh giá (Cán bộ có thể chỉnh sửa)
                </h3>
                <textarea 
                  rows={12} 
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="Đoạn văn nhận định của AI sẽ hiển thị ở đây..."
                  className="w-full bg-slate-955 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-sans custom-scrollbar flex-1 resize-none bg-slate-950"
                />
              </div>
            </div>
          </section>

        </main>
      </div>

      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        © 2026 Ủy ban nhân dân cấp phường. Thiết kế React Frontend di trú thông suốt - Production Ready.
      </footer>
    </div>
  )
}

export default App
