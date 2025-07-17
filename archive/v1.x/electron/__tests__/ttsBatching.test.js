jest.useFakeTimers();

describe('TTS Batching Logic', () => {
  let buffer, trigger, called;
  beforeEach(() => {
    buffer = '';
    called = false;
    trigger = jest.fn((text) => { called = text; });
  });
  function addToken(token, chunkSize, pauseMs) {
    buffer += token;
    if (buffer.length >= chunkSize) {
      trigger(buffer);
      buffer = '';
    } else {
      clearTimeout(global.ttsTimeout);
      global.ttsTimeout = setTimeout(() => {
        trigger(buffer);
        buffer = '';
      }, pauseMs);
    }
  }
  it('should trigger after chunk size', () => {
    addToken('a', 3, 1000);
    addToken('b', 3, 1000);
    addToken('c', 3, 1000);
    expect(trigger).toHaveBeenCalledWith('abc');
  });
  it('should trigger after pause', () => {
    addToken('a', 5, 1000);
    jest.advanceTimersByTime(1000);
    expect(trigger).toHaveBeenCalledWith('a');
  });
}); 