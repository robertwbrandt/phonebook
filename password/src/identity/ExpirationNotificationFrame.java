package identity;

import java.awt.*;
import java.awt.event.*;
import javax.swing.*;
import javax.swing.event.*;


/**
 * <p>Title: ExprationNotification</p>
 * <p>Description: Scan eDirectory and notify users when password about to expire</p>
 * <p>Copyright: Copyright (c) 2003</p>
 * <p>Company: Novell</p>
 * @author Paul Sherman
 * @version 1.0
 */

public class ExpirationNotificationFrame extends JFrame{
  JPanel contentPane;
  JMenuBar jMenuBar1 = new JMenuBar();
  JMenu jMenuFile = new JMenu();
  JMenuItem jMenuFileExit = new JMenuItem();
  JMenu jMenuHelp = new JMenu();
  JMenuItem jMenuHelpAbout = new JMenuItem();
  BorderLayout borderLayout1 = new BorderLayout();
  // JList jList1 = new JList();
  JList jList1;
  DefaultListModel listModel;
  JScrollPane scrollPane;

  //Construct the frame
  public ExpirationNotificationFrame() {
    enableEvents(AWTEvent.WINDOW_EVENT_MASK);
    try {
      jbInit();
    }
    catch(Exception e) {
      e.printStackTrace();
    }
  }
  //Component initialization
  private void jbInit() throws Exception  {
    contentPane = (JPanel) this.getContentPane();
    contentPane.setLayout(borderLayout1);
    this.setSize(new Dimension(400, 300));
    this.setTitle("Password Expiration Notification");
    jMenuFile.setText("File");
    jMenuFileExit.setText("Exit");
    jMenuFileExit.addActionListener(new ExpirationNotificationFrame_jMenuFileExit_ActionAdapter(this));
    jMenuHelp.setText("Help");
    jMenuHelpAbout.setText("About");
    jMenuHelpAbout.addActionListener(new ExpirationNotificationFrame_jMenuHelpAbout_ActionAdapter(this));
    jMenuFile.add(jMenuFileExit);
    jMenuHelp.add(jMenuHelpAbout);
    jMenuBar1.add(jMenuFile);
    jMenuBar1.add(jMenuHelp);

    listModel = new DefaultListModel();

    jList1 = new JList(listModel);
    jList1.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
    JScrollPane listScrollPane = new JScrollPane(jList1);

    contentPane.add(listScrollPane, BorderLayout.CENTER);
    this.setJMenuBar(jMenuBar1);
  }
  //File | Exit action performed
  public void jMenuFileExit_actionPerformed(ActionEvent e) {
    System.exit(0);
  }
  //Help | About action performed
  public void jMenuHelpAbout_actionPerformed(ActionEvent e) {
    ExpirationNotificationFrame_AboutBox dlg = new ExpirationNotificationFrame_AboutBox(this);
    Dimension dlgSize = dlg.getPreferredSize();
    Dimension frmSize = getSize();
    Point loc = getLocation();
    dlg.setLocation((frmSize.width - dlgSize.width) / 2 + loc.x, (frmSize.height - dlgSize.height) / 2 + loc.y);
    dlg.setModal(true);
    dlg.pack();
    dlg.show();
  }
  //Overridden so we can exit when window is closed
  protected void processWindowEvent(WindowEvent e) {
    super.processWindowEvent(e);
    if (e.getID() == WindowEvent.WINDOW_CLOSING) {
      jMenuFileExit_actionPerformed(null);
    }
  }

  public void addListItem(String text)
  {
  listModel.addElement(text);
  jList1.setSelectedIndex(listModel.getSize()-1);
  jList1.ensureIndexIsVisible(listModel.getSize()-1);
  }



}

class ExpirationNotificationFrame_jMenuFileExit_ActionAdapter implements ActionListener {
  ExpirationNotificationFrame adaptee;

  ExpirationNotificationFrame_jMenuFileExit_ActionAdapter(ExpirationNotificationFrame adaptee) {
    this.adaptee = adaptee;
  }
  public void actionPerformed(ActionEvent e) {
    adaptee.jMenuFileExit_actionPerformed(e);
  }
}

class ExpirationNotificationFrame_jMenuHelpAbout_ActionAdapter implements ActionListener {
  ExpirationNotificationFrame adaptee;

  ExpirationNotificationFrame_jMenuHelpAbout_ActionAdapter(ExpirationNotificationFrame adaptee) {
    this.adaptee = adaptee;
  }
  public void actionPerformed(ActionEvent e) {
    adaptee.jMenuHelpAbout_actionPerformed(e);
  }
}