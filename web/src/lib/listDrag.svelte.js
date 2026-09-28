// Drag and drop for the lists — shared by the desktop sidebar rail and the
// phone Holdings pane. Holdings rows are a copy source; list rows move within
// or across lists; list heads reorder the lists. The component renders
// previewLists() while a drag is live, so rows slide apart under it and a
// dashed slot marks where the row will land.
//
// Mouse: press and move 5px. Touch: hold still HOLD_MS, then drag. Moving
// first is a scroll or a pane swipe, never a drag.
import { get } from 'svelte/store';
import { lists, saveLists, rowFor } from './stores.js';

const SLOP = 5;
const HOLD_MS = 380;
const HOLD_SLOP = 8;

export function moveList(ls, id, index) {
  const L = ls.find((l) => l.id === id);
  const rest = ls.filter((l) => l.id !== id);
  return [...rest.slice(0, index), L, ...rest.slice(index)];
}

// list rows move out of their list; holdings stay put (copy). A zone target
// ('new' / 'remove') just takes the row out of its source list.
export function placeItem(ls, d, over) {
  const next = d.from === 'holdings'
    ? ls
    : ls.map((L) => (L.id === d.from ? { ...L, items: L.items.filter((i) => i.ticker !== d.ticker) } : L));
  if (over.zone) return next;
  return next.map((L) => {
    if (L.id !== over.listId) return L;
    const items = L.items.filter((i) => i.ticker !== d.ticker);
    const at = Math.min(over.index, items.length);
    return { ...L, items: [...items.slice(0, at), d.row, ...items.slice(at)] };
  });
}

// the layout a drop produces
export const dropLayout = (ls, d) =>
  d.kind === 'list' ? moveList(ls, d.listId, d.over.index) : placeItem(ls, d, d.over);

// what the lists render: the live preview while dragging, else the store
export const previewLists = (ls, drag) => (drag?.over ? dropLayout(ls, drag) : ls);

// the list whose row for drag.ticker renders as the dashed landing slot
export const slotListOf = (drag) =>
  drag?.kind !== 'item' ? null
    : drag.over?.listId ?? (drag.over || drag.from === 'holdings' ? null : drag.from);

const layoutKey = (ls) => JSON.stringify(ls.map((L) => [L.id, L.items.map((i) => i.ticker)]));

// write a drop, unless it landed where it started (a touch held and let go)
export function saveIfMoved(next) {
  return layoutKey(next) === layoutKey(get(lists) ?? []) ? Promise.resolve() : saveLists(next);
}

// the click that follows a mouse drop (same task as the pointerup) must not
// open the stock / fold the section. Touch never gets one: touchEnd cancels it.
function swallowClick() {
  const eat = (e) => { e.preventDefault(); e.stopPropagation(); };
  window.addEventListener('click', eat, { capture: true, once: true });
  setTimeout(() => window.removeEventListener('click', eat, { capture: true }), 0);
}

export class ListDrag {
  // { kind: 'item' | 'list', ticker, from, listId, row, label, touch,
  //   w, h, dx, dy, x, y, over } while dragging, else null
  drag = $state.raw(null);

  #o;
  #press = null;
  #timer = 0;
  #raf = 0;

  /**
   * @param {object} o
   * @param {() => HTMLElement} o.root       holds the [data-list] sections and [data-slot] rows; positioned, so offsets resolve against it
   * @param {() => HTMLElement} o.scroller   the element that scrolls
   * @param {() => {top: number, bottom: number}} [o.edges]  auto-scroll edges, default the scroller's box
   * @param {(id: number) => boolean} o.collapsed
   * @param {() => boolean} [o.canStart]
   * @param {(d: object) => void} o.onDrop   d.over says where
   */
  constructor(o) { this.#o = o; }

  // use:grab={meta} on a holding row, list row or list head.
  // meta: { kind: 'item', ticker, from: 'holdings' | listId, row? } | { kind: 'list', listId, label }
  grab = (node, meta) => {
    let m = meta;
    const mine = () => this.#press?.node === node;

    const down = (e) => {
      if (e.pointerType === 'touch' || e.button !== 0 || !this.#start(node, m, e.clientX, e.clientY, false)) return;
      window.addEventListener('pointermove', this.#pointerMove);
      window.addEventListener('pointerup', this.#drop);
      window.addEventListener('pointercancel', this.#end);
    };
    const touchStart = (e) => {
      if (e.touches.length !== 1) return this.#end();
      const t = e.touches[0];
      if (this.#start(node, m, t.clientX, t.clientY, true)) this.#timer = setTimeout(() => this.#begin(), HOLD_MS);
    };
    // Touch listeners sit on the node, not window: a touch keeps targeting the
    // element it began on after the preview re-renders that row out of the
    // DOM, and a detached node's events never reach window. Non-passive from
    // the start so a live drag can hold the pane still.
    const touchMove = (e) => {
      if (!mine()) return;
      const t = e.touches[0];
      const p = this.#press;
      if (!this.drag) {
        if (Math.hypot(t.clientX - p.x0, t.clientY - p.y0) > HOLD_SLOP) this.#end();
        else { p.x = t.clientX; p.y = t.clientY; }
        return;
      }
      if (e.cancelable) e.preventDefault();
      e.stopPropagation(); // the phone pager must not page under a drag
      this.#to(t.clientX, t.clientY);
    };
    const touchEnd = (e) => {
      if (!mine()) return;
      if (this.drag && e.cancelable) e.preventDefault(); // no tap click from a drop
      this.#drop();
    };
    const touchCancel = () => { if (mine()) this.#end(); };
    const noMenu = (e) => { if (mine() && this.#press.touch) e.preventDefault(); };

    node.addEventListener('pointerdown', down);
    node.addEventListener('touchstart', touchStart, { passive: true });
    node.addEventListener('touchmove', touchMove, { passive: false });
    node.addEventListener('touchend', touchEnd);
    node.addEventListener('touchcancel', touchCancel);
    node.addEventListener('contextmenu', noMenu);
    const off = () => {
      node.removeEventListener('pointerdown', down);
      node.removeEventListener('touchstart', touchStart);
      node.removeEventListener('touchmove', touchMove);
      node.removeEventListener('touchend', touchEnd);
      node.removeEventListener('touchcancel', touchCancel);
      node.removeEventListener('contextmenu', noMenu);
    };
    return {
      update: (next) => { m = next; },
      // the row under a live touch can be re-rendered away mid-drag; it keeps
      // its listeners until the drag ends
      destroy: () => { if (mine()) this.#press.cleanup = off; else off(); },
    };
  };

  #start(node, meta, x, y, touch) {
    this.#end();
    if (this.#o.canStart?.() === false) return false;
    this.#press = { ...meta, node, touch, x0: x, y0: y, x, y, cleanup: null };
    window.addEventListener('keydown', this.#key);
    return true;
  }

  #begin(x = this.#press?.x, y = this.#press?.y) {
    const p = this.#press;
    if (!p) return;
    clearTimeout(this.#timer);
    const r = p.node.getBoundingClientRect();
    this.drag = {
      kind: p.kind, ticker: p.ticker, from: p.from, listId: p.listId, label: p.label,
      row: p.kind === 'item' ? (p.row ?? rowFor(p.ticker)) : null, touch: p.touch,
      w: r.width, h: r.height, dx: p.x0 - r.left, dy: p.y0 - r.top, x, y, over: null,
    };
    document.documentElement.classList.add('list-dragging');
    window.getSelection()?.removeAllRanges();
    if (p.touch) navigator.vibrate?.(10);
    this.#raf = requestAnimationFrame(this.#autoScroll);
    this.#to(x, y);
  }

  #to(x, y) {
    this.drag = { ...this.drag, x, y, over: this.#hit(x, y) };
  }

  #pointerMove = (e) => {
    const p = this.#press;
    if (!p) return;
    if (this.drag) this.#to(e.clientX, e.clientY);
    else if (Math.hypot(e.clientX - p.x0, e.clientY - p.y0) >= SLOP) this.#begin(e.clientX, e.clientY);
  };

  #key = (e) => { if (e.key === 'Escape') this.#end(); };

  #drop = () => {
    const d = this.drag;
    this.#end();
    if (d?.over) this.#o.onDrop(d);
  };

  #end = () => {
    const p = this.#press;
    clearTimeout(this.#timer);
    cancelAnimationFrame(this.#raf);
    window.removeEventListener('pointermove', this.#pointerMove);
    window.removeEventListener('pointerup', this.#drop);
    window.removeEventListener('pointercancel', this.#end);
    window.removeEventListener('keydown', this.#key);
    document.documentElement.classList.remove('list-dragging');
    if (this.drag && !this.drag.touch) swallowClick();
    this.#press = null;
    this.drag = null;
    p?.cleanup?.();
  };

  // scroll while the pointer rides the top/bottom edge
  #autoScroll = () => {
    const d = this.drag;
    const sc = this.#o.scroller();
    if (!d || !sc) return;
    const { top, bottom } = this.#o.edges?.() ?? sc.getBoundingClientRect();
    const edge = d.touch ? 56 : 36;
    let v = 0;
    if (d.y < top + edge && d.y > top - edge) v = -Math.ceil((top + edge - d.y) / 4);
    else if (d.y > bottom - edge && d.y <= bottom) v = Math.ceil((d.y - (bottom - edge)) / 4);
    if (v) {
      const was = sc.scrollTop;
      sc.scrollTop += v;
      if (sc.scrollTop !== was) this.drag = { ...d, over: this.#hit(d.x, d.y) };
    }
    this.#raf = requestAnimationFrame(this.#autoScroll);
  };

  // layout position inside root (offsetTop ignores the flip transforms mid-animation)
  #top(el) {
    const root = this.#o.root();
    let t = 0;
    while (el && el !== root) { t += el.offsetTop; el = el.offsetParent; }
    return t;
  }

  #hit(x, y) {
    const d = this.drag;
    const zone = document.elementFromPoint(x, y)?.closest('[data-zone]');
    if (zone) return { zone: zone.dataset.zone };
    const root = this.#o.root();
    const r = this.#o.scroller().getBoundingClientRect();
    if (x < r.left - 24 || x > r.right + 24 || y < r.top || y > r.bottom) return null;
    const cy = y - root.getBoundingClientRect().top + root.scrollTop;
    const secs = [...root.querySelectorAll('[data-list]')];
    if (d.kind === 'list') {
      const others = secs.filter((s) => +s.dataset.list !== d.listId);
      return { index: others.filter((s) => this.#top(s) + s.offsetHeight / 2 < cy).length };
    }
    // no dead space under the holdings: a gap belongs to the list below it and
    // everything past the last list appends to it — otherwise a preview that
    // shifts the layout can leave the pointer in a gap, revert, and flicker
    if (!secs.length || cy < this.#top(secs[0]) - 6) return null;
    const s = secs.find((el) => cy <= this.#top(el) + el.offsetHeight + 6) ?? secs[secs.length - 1];
    const id = +s.dataset.list;
    if (this.#o.collapsed(id)) {
      const L = (get(lists) ?? []).find((l) => l.id === id);
      return { listId: id, index: L ? L.items.filter((i) => i.ticker !== d.ticker).length : 0 };
    }
    const slots = [...s.querySelectorAll('[data-slot]')].filter((el) => el.dataset.slot !== d.ticker);
    return { listId: id, index: slots.filter((el) => this.#top(el) + el.offsetHeight / 2 < cy).length };
  }
}
