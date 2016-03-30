package identity;

import javax.swing.UIManager;
import java.awt.*;
import java.io.*;
import java.text.*;
import java.util.*;
import javax.naming.*;
import javax.naming.directory.*;
import javax.naming.ldap.*;
import javax.mail.internet.*;
import javax.mail.*;
import java.math.*;

/**
 * <p>Title: ExprationNotification</p>
 * <p>Description: Scan eDirectory and notify users when password about to expire</p>
 * <p>Copyright: Copyright (c) 2003</p>
 * <p>Company: Novell</p>
 * @author Paul Sherman
 * @version 1.0
 */

public class ExpirationNotification
{
  // these are overridden by settings in config.xml
  boolean DEBUG_INFO_ON=false;
  boolean SEND_MSG=false;
  boolean SEND_TESTING=false;
  boolean SECURE_LDAP=false;
  boolean DISPLAY_GUI=false;
  boolean CONFIG_LOADED=false;

  boolean packFrame = false;
  ExpirationNotificationFrame frame;
  String notifyFromEmail=null, notifyFromText=null, notifyDays=null,
      notifyMessage=null, notifySubject=null, notifyTree=null, notifyServer=null,
      notifyLogin=null, notifyPassword=null, notifyBaseContext=null,
      notifyEventAddress=null, notifyEventTo=null, notifyMailHost=null, notifyPasswordURL=null;

  Hashtable messageTable;
  int maxDays=0, minDays=999999, msgcount=0;
  PrintWriter log=null;
  StringBuffer eventmessage=null;

  //Construct the application
  public ExpirationNotification()
  {

    eventmessage=new StringBuffer();
    eventmessage.append("<html><head><title>Notification Log</title>"+
                        "<style type=\"text/css\">"+
                        ".body {font-family: \"arial\", verdana; font-size: 10pt; font-weight: normal;}"+
                        ".head {font-family: \"arial\", verdana; font-size: 10pt; font-weight: bold;}"+
                        "</style>"+
                        "</head><body><table align=\"middle\">"+
                        "<tr><td class=\"head\">Name</td><td class=\"head\">Email</td><td class=\"head\">DN</td><td class=\"head\"align=\"right\">Exp Days</td></tr>");

    messageTable=new Hashtable();

    CONFIG_LOADED=getConfiguration();
    if(DISPLAY_GUI)
      {
        frame = new ExpirationNotificationFrame();
        //Validate frames that have preset sizes
        //Pack frames that have useful preferred size info, e.g. from their layout
        if (packFrame)
        {
          frame.pack();
        }
        else
        {
          frame.validate();
        }
        //Center the window
        Dimension screenSize = Toolkit.getDefaultToolkit().getScreenSize();
        Dimension frameSize = frame.getSize();
        if (frameSize.height > screenSize.height)
        {
          frameSize.height = screenSize.height;
        }
        if (frameSize.width > screenSize.width)
        {
          frameSize.width = screenSize.width;
        }
        frame.setLocation( (screenSize.width - frameSize.width) / 2,
                          (screenSize.height - frameSize.height) / 2);
        frame.setVisible(true);
      }
  }
  //Main method
  public static void main(String[] args) {
    try {
      UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
    }
    catch(Exception e) {
      e.printStackTrace();
    }
    new ExpirationNotification().Run();
  }

public void Run()
{
// 1. get last run timestamp
  long lastRunTimestamp=getLastRunTimestamp();
  long todayTimestamp=System.currentTimeMillis()/1000;



// testing
//lastRunTimestamp=todayTimestamp-(24*3600);

// 2. get congiguration
  if(CONFIG_LOADED)
  {



  // 3. scan users, check pw expiration, send appropriate messages
  scanPasswordExpirations(lastRunTimestamp,todayTimestamp);

// 5. update last run timestamp
  resetLastRunTimestamp(todayTimestamp);
  }
  else
  {
    writeConsole("Error: Unable to load configuration");
  }

eventmessage.append("</table></body></html>");
SendEventMessage(notifyEventAddress, notifyEventTo);
writeConsole("Done");
try
{
    Thread.sleep(2000);
}
catch(Exception e)
{
  e.printStackTrace();
}

if(DISPLAY_GUI) frame.dispose();
System.exit(0);
}

long getLastRunTimestamp()
{
long lastRun=0;
String slastRun=null;
StringBuffer dataline=new StringBuffer();
try
  {
    BufferedReader br = new BufferedReader(new FileReader("runtime.xml"));

    while(br.ready())
    {
      dataline.append(br.readLine());
    }

    lastRun=new Long(getTagValue(new String(dataline),"LastRunTimestamp",0)).longValue();
  }
catch(FileNotFoundException fnfe)
  {
  lastRun=0;
  }
catch(Exception e)
  {
  e.printStackTrace();
  }

//System.out.println(dataline);
return lastRun;
}

void resetLastRunTimestamp(long timestamp)
{
  String doc="<?xml version=\"1.0\" standalone=\"yes\"?><ExpirationNotification><LastRunTimestamp>"+timestamp+"</LastRunTimestamp></ExpirationNotification>";
  try
    {
      BufferedWriter bw = new BufferedWriter(new FileWriter("runtime.xml"));
      bw.write(doc);
      bw.flush();
      bw.close();
    }
  catch(Exception e)
    {
    e.printStackTrace();
    }
}

boolean getConfiguration()
  {
  boolean ret=true;
  StringBuffer dataline=new StringBuffer();
  try
    {
      BufferedReader br = new BufferedReader(new FileReader("config.xml"));

      while(br.ready())
      {
        dataline.append(br.readLine()+"\n");
      }
    }
  catch(FileNotFoundException fnfe)
    {
      System.out.println("Can't open config.xml");
    }
  catch(Exception e)
    {
    e.printStackTrace();
    }

  String doc=new String(dataline);
  notifyTree=getTagValue(doc,"Tree",0);
  notifyServer=getTagValue(doc,"Server",0);
  notifyLogin=getTagValue(doc,"Login",0);
  notifyPassword=getTagValue(doc,"Password",0);
  notifyBaseContext=getTagValue(doc,"BaseContext",0);
  if(notifyBaseContext==null) notifyBaseContext=""; // search from root

  notifyFromEmail=getTagValue(doc,"FromEmailAddress",0);
  notifyFromText=getTagValue(doc,"FromText",0);
  notifySubject=getTagValue(doc,"Subject",0);
  notifyEventAddress=getTagValue(doc,"EventAddress",0);
  notifyEventTo=getTagValue(doc,"EventTo",0);
  notifyMailHost=getTagValue(doc,"MailHost",0);
  notifyPasswordURL=getTagValue(doc,"PasswordURL",0);

  String temp=getTagValue(doc,"SecureLDAP",0);
  if(temp!=null && temp.toLowerCase().startsWith("y")) SECURE_LDAP=true;
  temp=getTagValue(doc,"SendMsg",0);
  if(temp!=null && temp.toLowerCase().startsWith("y")) SEND_MSG=true;
  temp=getTagValue(doc,"DebugInfo",0);
  if(temp!=null && temp.toLowerCase().startsWith("y")) DEBUG_INFO_ON=true;
  temp=getTagValue(doc,"SendTest",0);
  if(temp!=null && temp.toLowerCase().startsWith("y")) SEND_TESTING=true;
  temp=getTagValue(doc,"DisplayGUI",0);
  if(temp!=null && temp.toLowerCase().startsWith("y")) DISPLAY_GUI=true;

  int p1=0, days=0;
  while(p1>=0)
  {
    p1 = findTag(doc, "Notify", p1);
    if(p1>=0)
    {
      notifyDays = getTagAttribute(doc, "days", p1);
      days=new Integer(notifyDays).intValue();
      if(days>maxDays) maxDays=days;
        else if(days<minDays) minDays=days;
      notifyMessage = getTagValue(doc, "Message", p1);
      messageTable.put(new Integer(notifyDays), notifyMessage);
      p1++;
    }
  }

return ret;
}

void scanPasswordExpirations(long lastRunTimestamp, long todayTimestamp)
{
  Hashtable env=new Hashtable();
  InitialLdapContext ldapCtx=null, novCtx=null;

  if(SECURE_LDAP) env.put(Context.SECURITY_PROTOCOL, "ssl");
  env.put(Context.INITIAL_CONTEXT_FACTORY,"com.sun.jndi.ldap.LdapCtxFactory");
  if(SECURE_LDAP) env.put(Context.PROVIDER_URL,"ldap://"+notifyServer+":636");
    else env.put(Context.PROVIDER_URL,"ldap://"+notifyServer+":389");
  env.put(Context.SECURITY_AUTHENTICATION, "simple");
  env.put(Context.SECURITY_PRINCIPAL, notifyLogin);
  env.put(Context.SECURITY_CREDENTIALS, notifyPassword);

  writeConsole("Connecting to "+notifyTree);

  try
  {
    ldapCtx = new InitialLdapContext(env, null);

    searchUsers(notifyBaseContext, ldapCtx, lastRunTimestamp, todayTimestamp);
  }
  catch(Exception e)
  {
    e.printStackTrace();
  }

  try
  {
    ldapCtx.close();
  }
  catch(Exception ec)
  {
    //ec.printStackTrace();
  }

}


void searchUsers(String baseContext, InitialLdapContext ctx, long lastRunTimestamp, long todayTimestamp)
{
  String dn=null;

  if(ctx!=null)
  {
    String[] attrIDs = {"objectClass","passwordExpirationTime","loginDisabled","loginGraceRemaining","mail","preferredName"};
    SearchControls ctls = new SearchControls();
    ctls.setReturningAttributes(attrIDs);

    String filter = "(|(o=*)(ou=*)(cn=*))";

      try
      {

        if(baseContext==null || baseContext.length()==0) System.out.println("Searching context: root");
          else System.out.println("Searching context: "+baseContext);

        NamingEnumeration answer = ctx.search(baseContext, filter, ctls);

        while (answer.hasMore())
        {
          dn = null;
          SearchResult sr = (SearchResult) answer.next();
          dn = sr.getName();
          if(baseContext.compareTo("")!=0) dn+=", "+baseContext;
          Attributes attrs = sr.getAttributes();
          Attribute attr = attrs.get("objectClass");

          if (attr != null)
          {
            for (NamingEnumeration e = attr.getAll(); e.hasMore(); )
            {
              String objectClass = (String) e.next();
              if (objectClass != null)
              {
                if (objectClass.compareTo("organization") == 0 ||
                    objectClass.compareTo("organizationalUnit") == 0)
                  searchUsers(dn, ctx, lastRunTimestamp, todayTimestamp);
                else if (objectClass.compareTo("inetOrgPerson") == 0)
                  ProcessUser(dn, attrs, lastRunTimestamp, todayTimestamp);
              }
            }
          }
        }
      }
      catch (Exception e)
      {
        e.printStackTrace();
      }
  }
}


void ProcessUser(String dn, Attributes attrs, long lastRunTimestamp, long todayTimestamp)
{
  String pwexpiration=null, temp=null, graceLogins=null, cn=null;

  try
  {
    int p1 = dn.indexOf(",");
    if (p1 > 0)
      cn = dn.substring(3, p1).trim();
  }
  catch(Exception e)
  {
    cn=dn;
  }


  try
  {
    Attribute attr = attrs.get("passwordExpirationTime");

    pwexpiration = null;
    if (attr != null)
    {
      for (NamingEnumeration e = attr.getAll(); e.hasMore(); )
      {
        temp = (String) e.next();
        if (temp != null)
        {
          if (temp.compareTo(" ") > 0 && temp.length() > 0)
            pwexpiration = temp;
        }
      }
    }

    attr = attrs.get("loginGraceRemaining");
    graceLogins = null;
    if (attr != null)
    {
      for (NamingEnumeration e = attr.getAll(); e.hasMore(); )
      {
        temp = (String) e.next();
        if (temp != null)
        {
          if (temp.compareTo(" ") > 0 && temp.length() > 0)
            graceLogins = temp;
        }
      }
    }

    if (graceLogins == null)
      graceLogins = "10";

    attr = attrs.get("mail");
    String emailAddress = null;
    if (attr != null)
    {
      for (NamingEnumeration e = attr.getAll(); e.hasMore(); )
      {
        temp = (String) e.next();
        if (temp != null)
        {
          if (temp.compareTo(" ") > 0 && temp.length() > 0)
            emailAddress = temp.toLowerCase();
        }
      }
    }

    if (emailAddress == null)
      emailAddress = notifyEventAddress;

    attr = attrs.get("preferredName");
    String fullName = null;
    if (attr != null)
    {
      for (NamingEnumeration e = attr.getAll(); e.hasMore(); )
      {
        temp = (String) e.next();
        if (temp != null)
        {
          if (temp.compareTo(" ") > 0 && temp.length() > 0)
            fullName = temp;
        }
      }
    }

    if (fullName == null)
      fullName = cn;

    attr = attrs.get("loginDisabled");
    boolean loginDisabled = false;
    if (attr != null)
    {
      for (NamingEnumeration e = attr.getAll(); e.hasMore(); )
      {
        temp = (String) e.next();
        if (temp != null)
        {
          if (temp.compareTo(" ") > 0 && temp.length() > 0)
            if (temp.trim().compareTo("TRUE") == 0)
              loginDisabled = true;
        }
      }
    }

    if (!loginDisabled && pwexpiration != null)
    {

      int expYear = new Integer(pwexpiration.substring(0, 4)).intValue();
      int expMonth = new Integer(pwexpiration.substring(4, 6)).intValue() - 1;
      int expDay = new Integer(pwexpiration.substring(6, 8)).intValue();
      int expHour = new Integer(pwexpiration.substring(8, 10)).intValue();
      int expMinute = new Integer(pwexpiration.substring(10, 12)).intValue();
      int expSecond = new Integer(pwexpiration.substring(12, 14)).intValue();

      Calendar cal = Calendar.getInstance();
      cal.set(Calendar.YEAR, expYear);
      cal.set(Calendar.MONTH, expMonth);
      cal.set(Calendar.DAY_OF_MONTH, expDay);
      cal.set(Calendar.HOUR_OF_DAY, expHour);
      cal.set(Calendar.MINUTE, expMinute);
      cal.set(Calendar.SECOND, expSecond);
      long expTimestamp = cal.getTimeInMillis() / 1000;
      long expRunDays = getDays(expTimestamp - lastRunTimestamp);
      long expNowDays = getDays(expTimestamp - todayTimestamp);

      boolean notifyNow = false;
      int msgkey = 0, daysPrior = 0;
      Integer daysPriorInt = null;

      if (expTimestamp < lastRunTimestamp)
      {
        // already expired...I've done everything I can do

        notifyNow = false;
        if (expNowDays == 0 || expNowDays == -3 ||
            expNowDays == -5 || expNowDays == -10 ||
            expNowDays == -15 || expNowDays == -30)
        {
          msgkey = 0;
          notifyNow = true;
        }
      }
      else if (expTimestamp < todayTimestamp)
      {
        // expired but you may not know yet, show grace login count
        msgkey = 0;
        notifyNow = true;
      }
      else if ( (expTimestamp - todayTimestamp) < (24 * 3600))
      {
        // will expire today, act now before it's too late
        msgkey = 0;
        notifyNow = true;
      }
      else
      {
        if (expNowDays >= minDays && expNowDays <= maxDays)
        {
          msgkey = maxDays;
          for (Enumeration e = messageTable.keys(); e.hasMoreElements(); )
          {
            daysPriorInt = (Integer) e.nextElement();
            daysPrior = daysPriorInt.intValue();
            if (expRunDays > daysPrior && expNowDays <= daysPrior)
            {
              if (daysPrior < msgkey)
                msgkey = daysPrior;
              notifyNow = true;
            }
          }
        }
      }

      if (notifyNow)
      {
        SendNotification(emailAddress, fullName, dn, expNowDays, graceLogins,
                         (String) messageTable.get(new Integer(msgkey)));
      }
    }
  }
  catch(Exception e)
  {
    e.printStackTrace();
  }

}


String formatDN(String ndsDN)
        {
        String ldapDN="cn=";
        int p1=0, p2=0, cnt=0;

        if(ndsDN==null) return null;

        while(p2>=0)
                {
                p2=ndsDN.indexOf(".",p1);
                if(p2<0) break;
                while(p2<=p1)
                        {
                        p1++;
                        p2=ndsDN.indexOf(".",p1);
                        }

                if(cnt==0) ldapDN+=ndsDN.substring(p1,p2);
                        else ldapDN+=", ou="+ndsDN.substring(p1,p2);
                cnt++;
                p1=p2+1;
                }

        if(cnt>0) ldapDN+=", o="+ndsDN.substring(p1);
                else ldapDN+=ndsDN;


        System.out.println("formatDn: "+ndsDN+" "+ldapDN);

        return ldapDN;
        }


  void SendEventMessage(String emailAddress, String fullName)
  {
    try
      {
      Properties props=new Properties();
      props.put("mail.host",notifyMailHost);
      Session mailConnection=Session.getInstance(props,null);
      Message msg=new MimeMessage(mailConnection);
      InternetAddress toAddr=new InternetAddress(emailAddress,fullName);

      InternetAddress fromAddr=new InternetAddress(notifyEventAddress, notifyFromText);
      msg.setFrom(fromAddr);
      msg.setRecipient(Message.RecipientType.TO,toAddr);
      msg.setSubject("Notification Log");
      msg.addHeader("X-Priority","1");
      msg.addHeader("X-MSMail-Priority","High");

      MimeBodyPart mbp1 = new MimeBodyPart();
      mbp1.setContent("Messages: "+msgcount,"text/plain");
      MimeBodyPart mbp2 = new MimeBodyPart();
      mbp2.setContent(new String(eventmessage),"text/html");
      Multipart mp = new MimeMultipart("alternative");
      mp.addBodyPart(mbp1);
      mp.addBodyPart(mbp2);
      msg.setContent(mp);

      Transport.send(msg);
      System.out.println("Sent event message to "+emailAddress);
      }
    catch(Exception e)
      {
      e.printStackTrace();
      }
  }

void SendNotification(String emailAddress, String fullName, String dn, long expdays, String gracelogins, String messageTemplate)
{
  String messageContent=messageTemplate;
  String temp=null;

  int p1=0;

  if(expdays>0)
  {
    writeConsole(fullName + " expires in " + expdays + " days");
  }
  else
  {
    writeConsole(fullName + " has expired");
  }

  while((p1=messageContent.indexOf("%days%",p1))>=0)
  {
    temp=messageContent.substring(0,p1) + expdays + messageContent.substring(p1+6);
    messageContent=temp;
  }

  while((p1=messageContent.indexOf("%grace%",p1))>=0)
  {
    temp=messageContent.substring(0,p1) + gracelogins + messageContent.substring(p1+7);
    messageContent=temp;
  }

  while((p1=messageContent.indexOf("%pwurl%",p1))>=0)
  {
    temp=messageContent.substring(0,p1) + notifyPasswordURL + messageContent.substring(p1+7);
    messageContent=temp;
  }

  String textContent=getTextContent(expdays,gracelogins);

  try
    {
    Properties props=new Properties();
    props.put("mail.host",notifyMailHost);
    Session mailConnection=Session.getInstance(props,null);
    Message msg=new MimeMessage(mailConnection);

    InternetAddress toAddr=null;

    if(!SEND_TESTING) toAddr=new InternetAddress(emailAddress,fullName);
      else toAddr=new InternetAddress(notifyEventAddress,fullName);

    InternetAddress fromAddr=new InternetAddress(notifyFromEmail,notifyFromText);
    msg.setFrom(fromAddr);
    msg.setRecipient(Message.RecipientType.TO,toAddr);
    if(!DEBUG_INFO_ON) msg.setSubject(notifySubject);
      else msg.setSubject("Notify: "+dn);
    msg.addHeader("X-Priority","1");
    msg.addHeader("X-MSMail-Priority","High");

    MimeBodyPart mbp1 = new MimeBodyPart();
    mbp1.setContent(textContent,"text/plain");
    MimeBodyPart mbp2 = new MimeBodyPart();
    mbp2.setContent(messageContent,"text/html");
    Multipart mp = new MimeMultipart("alternative");
    mp.addBodyPart(mbp1);
    mp.addBodyPart(mbp2);
    msg.setContent(mp);

    if(SEND_MSG) Transport.send(msg);
    msgcount++;
    System.out.println("Sent notification to "+emailAddress+" "+dn+" "+expdays);
    writeLog(fullName,emailAddress,dn,expdays);
    }
  catch(Exception e)
    {
      System.out.println("**Send FAILED to "+emailAddress+" "+expdays);
    }

  try
    {
//        Thread.sleep(2000);
    }
  catch(Exception e)
    {
      e.printStackTrace();
    }


}

long getDays(long seconds)
  {
  long days=seconds/(3600*24);
  return days;
  }

String getTagValue(String sourceDoc, String tag, int startpos)
  {
  String value=null, starttag="<"+tag+">", endtag="</"+tag+">";
  int p1=0, p2=0;

  p1=sourceDoc.indexOf(starttag, startpos);
  if(p1>=0)
    {
    p2=sourceDoc.indexOf(endtag, p1);
    if(p2>=0) value=sourceDoc.substring(p1+starttag.length(),p2);
    }
  return value;
  }

  String getTagAttribute(String sourceDoc, String attribname, int startpos)
    {
    String value=null, attrib=attribname+"=\"";
    int p1=0, p2=0;

    try
    {
      p1 = sourceDoc.indexOf(attrib, startpos);
      if (p1 >= 0)
      {
        p2 = sourceDoc.indexOf("\"", p1 + attrib.length());
        if (p2 >= 0) value = sourceDoc.substring(p1 + attrib.length(), p2);
      }
    }
    catch(Exception e)
    {
      e.printStackTrace();
    }
    return value;
    }

  int findTag(String sourceDoc, String tag, int startpos)
    {
    String value=null, starttag="<"+tag;

    return sourceDoc.indexOf(starttag,startpos);
    }

String getTextContent(long expdays, String gracelogins)
  {
    String textContent="* Your password ";

    if(expdays==1) textContent+="will expire tomorrow.\n\nPlease change your password immediately to prevent interruption of business services.";
      else if(expdays<=0) textContent+="has expired.  You have "+gracelogins+" grace logins remaining.\n\nPlease change your password immediately to prevent interruption of business services.";
        else textContent+="will expire in "+expdays+" days.\n\nPlease change your password at your earliest opportunity to prevent interruption of business services.";

    textContent+="\n\nPassword Self-Service can be found at:\n\n"+
                 "   "+notifyPasswordURL+" ";

    return textContent;
  }

void writeLog(String name, String email, String dn, long expdays)
  {
    TimeZone tz = TimeZone.getTimeZone("GMT+0");
    Calendar cal = Calendar.getInstance(tz);    // getInstance() assumes local
    java.util.Date calTime = cal.getTime();
    String timestamp=(new SimpleDateFormat("yyyyMMdd HHmmss").format(calTime));

    String eventline="<tr><td class=\"body\">"+name+"</td><td class=\"body\">"+email+"</td><td class=\"body\">"+dn+"</td><td class=\"body\" align=\"right\">"+expdays+"</td></tr>";
    try
    {
      log = new PrintWriter(new FileWriter("notify.log", true));
      log.println(timestamp + " " + name + " " + email + " " + expdays);
      log.close();
    }
    catch(Exception e)
    {
      e.printStackTrace();
    }
    eventmessage.append(eventline);
  }

void writeConsole(String text)
  {
    if(DISPLAY_GUI) frame.addListItem(text);
      else System.out.println(text);
  }
}