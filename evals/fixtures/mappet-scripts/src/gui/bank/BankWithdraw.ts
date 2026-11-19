class BankWithdraw {
  private data = { limit: 100 };
  static handleMain(c: any) {
    const gui = new BankWithdraw();
    const ui = mappet.createUI(c, 'handler');
    ui.button('Снять').id('withdraw');
    new Callback('confirm', c.player.uniqueId).setFunction(() => BankOperations.withdraw(c.player, gui.data.limit));
    c.player.openUI(ui);
  }
}
