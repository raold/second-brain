/**
 * @jest-environment jsdom
 */
test('localStorage works', () => {
  window.localStorage.setItem('foo', 'bar');
  expect(window.localStorage.getItem('foo')).toBe('bar');
}); 