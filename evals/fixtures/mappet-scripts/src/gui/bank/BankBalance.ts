/** ID of the shared handler function from libs/Callback.js. */
const BANK_BALANCE_HANDLER: string = 'handler';

/** ID of the close action. */
const BANK_BALANCE_CLOSE: string = 'close';

/** E key code. */
const BANK_BALANCE_CLOSE_KEY: number = 18;

/** Tooltip for the close key. */
const BANK_BALANCE_CLOSE_HINT: string = '';

/** Title of the balance window. */
const BANK_BALANCE_TITLE: string = 'Баланс';

/** Window width. */
const BANK_BALANCE_WIDTH: number = 160;

/** Window height. */
const BANK_BALANCE_HEIGHT: number = 80;

/** Offset at half the size of a container. */
const BANK_BALANCE_CENTER: number = 0.5;

/** Margin outside the stack. */
const BANK_BALANCE_MARGIN: number = 0;

/** Padding inside the stack. */
const BANK_BALANCE_PADDING: number = 8;

/** Opens the read-only balance window. */
class BankBalance {
  /** Opens the window for the current player. */
  public static handleMain(c: IScriptEvent): void {
    const ui: IMappetUIBuilder = mappet.createUI(c, BANK_BALANCE_HANDLER).background();
    const layout: IMappetUIBuilder = ui.layout();

    layout.getCurrent()
      .wh(BANK_BALANCE_WIDTH, BANK_BALANCE_HEIGHT)
      .rxy(BANK_BALANCE_CENTER, BANK_BALANCE_CENTER)
      .anchor(BANK_BALANCE_CENTER, BANK_BALANCE_CENTER)
      .keybind(BANK_BALANCE_CLOSE_KEY, BANK_BALANCE_CLOSE, BANK_BALANCE_CLOSE_HINT);

    const body: IMappetUIBuilder = layout.column(BANK_BALANCE_MARGIN, BANK_BALANCE_PADDING);
    body.label(BANK_BALANCE_TITLE);

    new Callback(BANK_BALANCE_CLOSE, c.player.uniqueId).setFunction(() => c.player.closeUI());
    c.player.openUI(ui);
  }
}

/** Entry point of the balance script. */
// @ts-ignore
function main(c: IScriptEvent): void {
  BankBalance.handleMain(c);
}
