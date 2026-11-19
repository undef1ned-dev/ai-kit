/** Event passed to the entry point and callbacks. */
declare interface IScriptEvent {
  /** Player who triggered the event. */
  player: IScriptPlayer;
}

/** Player API used by the fixture windows. */
declare interface IScriptPlayer {
  /** Stable player ID. */
  uniqueId: string;
  /** Opens the built window. */
  openUI(ui: IMappetUIBuilder): void;
  /** Closes the current window. */
  closeUI(): void;
}

/** Builder API for the project layout pattern. */
declare interface IMappetUIBuilder {
  background(): IMappetUIBuilder;
  layout(): IMappetUIBuilder;
  getCurrent(): UIComponent;
  column(margin: number, padding: number): IMappetUIBuilder;
  label(text: string): UIComponent;
  button(text: string): UIComponent;
}

/** Component API used in the fixture. */
declare interface UIComponent {
  id(id: string): UIComponent;
  wh(width: number, height: number): UIComponent;
  rxy(x: number, y: number): UIComponent;
  anchor(x: number, y: number): UIComponent;
  keybind(key: number, action: string, label: string): UIComponent;
}

/** Global Mappet factory. */
declare const mappet: {
  createUI(c: IScriptEvent, handler: string): IMappetUIBuilder;
};

/** Registers player-scoped handlers for interactive elements. */
declare class Callback {
  constructor(id: string, uuid: string);
  setFunction(handler: (c: IScriptEvent) => void): Callback;
}
