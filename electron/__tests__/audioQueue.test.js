describe('Audio Queue', () => {
  let audioQueue, currentAudioIdx, played;
  beforeEach(() => {
    audioQueue = [];
    currentAudioIdx = -1;
    played = [];
    global.Audio = function(url) {
      this.url = url;
      this.play = () => { played.push(url); if (this.onended) setTimeout(this.onended, 10); };
    };
  });
  function playAudioChunk(idx) {
    if (audioQueue[idx]) {
      const audio = new Audio(audioQueue[idx].url);
      currentAudioIdx = idx;
      audio.onended = () => {
        if (audioQueue[idx+1]) playAudioChunk(idx+1);
        else currentAudioIdx = -1;
      };
      audio.play();
    }
  }
  it('should play all chunks in order', (done) => {
    audioQueue = [{url:'a'},{url:'b'},{url:'c'}];
    playAudioChunk(0);
    setTimeout(() => {
      expect(played).toEqual(['a','b','c']);
      done();
    }, 50);
  });
  it('should replay a chunk', () => {
    audioQueue = [{url:'a'},{url:'b'}];
    playAudioChunk(1);
    expect(played).toEqual(['b']);
  });
}); 