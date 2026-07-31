function requiredText(value, name) {
  const text = String(value || '').trim();
  if (!text) throw new Error(`${name} is required`);
  return text;
}

function taskErrorCode(error) {
  const value = String(error?.code || 'ANALYSIS_FAILED').toUpperCase();
  const normalized = value.replace(/[^A-Z0-9_-]/g, '_').slice(0, 80);
  return normalized || 'ANALYSIS_FAILED';
}

export async function runTrackedAnalysis({
  api,
  invoke,
  persist,
  taskType,
  title,
  requestRef,
  moduleCode = 'MULTIMODAL_AGENT'
}) {
  if (typeof api !== 'function') throw new Error('api is required');
  if (typeof invoke !== 'function') throw new Error('invoke is required');

  const task = await api('/tasks', {
    method: 'POST',
    body: JSON.stringify({
      moduleCode: requiredText(moduleCode, 'moduleCode'),
      taskType: requiredText(taskType, 'taskType'),
      title: requiredText(title, 'title'),
      requestRef: requiredText(requestRef, 'requestRef').slice(0, 200)
    })
  });
  const taskId = requiredText(task?.id, 'task.id');
  const taskPath = `/tasks/${encodeURIComponent(taskId)}/status`;

  try {
    await api(taskPath, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'RUNNING', progress: 10 })
    });
    const gateway = await invoke();
    const record = typeof persist === 'function' ? await persist({ gateway, task }) : null;
    const resultRef = String(record?.id || gateway?.callId || gateway?.requestId || requestRef).slice(0, 200);
    const completedTask = await api(taskPath, {
      method: 'PATCH',
      body: JSON.stringify({
        status: 'SUCCEEDED',
        progress: 100,
        resultRef
      })
    });
    return { gateway, task: completedTask, record };
  } catch (error) {
    try {
      await api(taskPath, {
        method: 'PATCH',
        body: JSON.stringify({
          status: 'FAILED',
          errorCode: taskErrorCode(error),
          errorMessage: '分析请求失败，请根据 requestId 和 AI 调用日志排查。'
        })
      });
    } catch (trackingError) {
      error.taskTrackingError = trackingError;
    }
    error.taskId = taskId;
    throw error;
  }
}
