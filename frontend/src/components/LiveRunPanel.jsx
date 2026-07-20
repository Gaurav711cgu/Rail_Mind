import { useState, useEffect } from 'react';
import { Terminal, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

const LiveRunPanel = () => {
  const [activeRuns, setActiveRuns] = useState(0);
  const [lastStatus, setLastStatus] = useState('Idle');
  
  useEffect(() => {
    // Connect to SSE stream
    const eventSource = new EventSource('/api/v1/live/stream');
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setActiveRuns(data.active_runs);
      if (data.active_runs > 0) {
        setLastStatus('Running Agent Cycle...');
      } else {
        setLastStatus((prevStatus) => {
          if (prevStatus === 'Running Agent Cycle...') {
            setTimeout(() => setLastStatus('Idle'), 3000);
            return 'Completed';
          }
          return prevStatus;
        });
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE Error', error);
      eventSource.close();
    };
    
    return () => {
      eventSource.close();
    };
  }, []);
  
  if (activeRuns === 0 && lastStatus === 'Idle') return null;

  return (
    <div className="fixed bottom-6 right-6 w-80 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-50">
      <div className="flex items-center gap-2 p-3 bg-slate-800/50 border-b border-slate-700">
        <Terminal className="w-4 h-4 text-cyan-400" />
        <span className="text-sm font-semibold text-slate-200">Live Agent Execution</span>
      </div>
      
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400 flex items-center gap-1.5">
            {activeRuns > 0 ? (
              <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
            ) : lastStatus === 'Completed' ? (
              <CheckCircle2 className="w-4 h-4 text-green-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-slate-500" />
            )}
            Status
          </span>
          <span className={`font-mono ${activeRuns > 0 ? 'text-amber-400' : 'text-slate-300'}`}>
            {lastStatus}
          </span>
        </div>
        
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Active Threads</span>
          <span className="font-mono text-cyan-400">{activeRuns}</span>
        </div>
      </div>
    </div>
  );
};

export default LiveRunPanel;
