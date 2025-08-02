import javax.swing.*;
import java.awt.*;
// import java.awt.event.*;
import java.util.*;

public class LibraryManagementSystem extends JFrame {
    private java.util.List<Book> books = new ArrayList<>();
    private java.util.List<Member> members = new ArrayList<>();
    private java.util.List<Issue> issues = new ArrayList<>();

    private JComboBox<String> bookBox, memberBox;
    private DefaultListModel<String> issueListModel;

    public LibraryManagementSystem() {
        setTitle("Library Management System");
        setSize(600, 400);
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setLocationRelativeTo(null);

        JTabbedPane tabs = new JTabbedPane();
        tabs.add("Books", createBookPanel());
        tabs.add("Members", createMemberPanel());
        tabs.add("Issue/Return", createIssuePanel());

        add(tabs);
    }

    private JPanel createBookPanel() {
        JPanel panel = new JPanel(new BorderLayout());
        DefaultListModel<String> model = new DefaultListModel<>();
        JList<String> list = new JList<>(model);

        JTextField titleField = new JTextField(10);
        JTextField authorField = new JTextField(10);
        JButton add = new JButton("Add");
        JButton del = new JButton("Delete");

        JPanel form = new JPanel();
        form.add(new JLabel("Title:"));
        form.add(titleField);
        form.add(new JLabel("Author:"));
        form.add(authorField);
        form.add(add);
        form.add(del);

        panel.add(form, BorderLayout.NORTH);
        panel.add(new JScrollPane(list), BorderLayout.CENTER);

        add.addActionListener(e -> {
            String title = titleField.getText();
            String author = authorField.getText();
            if (!title.isEmpty() && !author.isEmpty()) {
                Book b = new Book(title, author);
                books.add(b);
                model.addElement(b.toString());
                bookBox.addItem(b.toString());
            }
        });

        del.addActionListener(e -> {
            int i = list.getSelectedIndex();
            if (i >= 0) {
                books.remove(i);
                model.remove(i);
                bookBox.removeItemAt(i);
            }
        });

        return panel;
    }

    private JPanel createMemberPanel() {
        JPanel panel = new JPanel(new BorderLayout());
        DefaultListModel<String> model = new DefaultListModel<>();
        JList<String> list = new JList<>(model);

        JTextField nameField = new JTextField(10);
        JButton add = new JButton("Add");
        JButton del = new JButton("Delete");

        JPanel form = new JPanel();
        form.add(new JLabel("Name:"));
        form.add(nameField);
        form.add(add);
        form.add(del);

        panel.add(form, BorderLayout.NORTH);
        panel.add(new JScrollPane(list), BorderLayout.CENTER);

        add.addActionListener(e -> {
            String name = nameField.getText();
            if (!name.isEmpty()) {
                Member m = new Member(name);
                members.add(m);
                model.addElement(m.toString());
                memberBox.addItem(m.toString());
            }
        });

        del.addActionListener(e -> {
            int i = list.getSelectedIndex();
            if (i >= 0) {
                members.remove(i);
                model.remove(i);
                memberBox.removeItemAt(i);
            }
        });

        return panel;
    }

    private JPanel createIssuePanel() {
        JPanel panel = new JPanel(new BorderLayout());
        JPanel form = new JPanel();

        bookBox = new JComboBox<>();
        memberBox = new JComboBox<>();
        JButton issueBtn = new JButton("Issue");
        JButton returnBtn = new JButton("Return");

        form.add(new JLabel("Book:"));
        form.add(bookBox);
        form.add(new JLabel("Member:"));
        form.add(memberBox);
        form.add(issueBtn);
        form.add(returnBtn);

        issueListModel = new DefaultListModel<>();
        JList<String> issueList = new JList<>(issueListModel);

        panel.add(form, BorderLayout.NORTH);
        panel.add(new JScrollPane(issueList), BorderLayout.CENTER);

        issueBtn.addActionListener(e -> {
            int bIdx = bookBox.getSelectedIndex();
            int mIdx = memberBox.getSelectedIndex();
            if (bIdx >= 0 && mIdx >= 0) {
                Issue i = new Issue(books.get(bIdx), members.get(mIdx));
                issues.add(i);
                issueListModel.addElement(i.toString());
            }
        });

        returnBtn.addActionListener(e -> {
            int i = issueList.getSelectedIndex();
            if (i >= 0) {
                issues.remove(i);
                issueListModel.remove(i);
            }
        });

        return panel;
    }

    // --- Models ---
    class Book {
        String title, author;
        Book(String t, String a) { title = t; author = a; }
        public String toString() { return title + " by " + author; }
    }

    class Member {
        String name;
        Member(String n) { name = n; }
        public String toString() { return name; }
    }

    class Issue {
        Book book;
        Member member;
        Date date = new Date();
        Issue(Book b, Member m) { book = b; member = m; }
        public String toString() {
            return member + " borrowed \"" + book + "\" on " + date.toString();
        }
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new LibraryManagementSystem().setVisible(true));
    }
}
