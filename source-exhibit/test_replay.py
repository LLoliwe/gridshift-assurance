import unittest
from fractions import Fraction
from replay import amount,reported,replay,QUESTION,UNAVAILABLE

def cell(v,t='n',fmt='#,##0'):return dict(source_text_or_numeric_token=v,xml_type=t,number_format=fmt,formula=None)
class Replay(unittest.TestCase):
 def test_durnacol_direction(self):
  r=replay(dict(current_source=cell('155.69'),prior_source=cell('146'),percentage_source=cell('▼-6.85','s','0.00%')));self.assertEqual(r['status'],QUESTION);self.assertEqual(r['exact_value_percentage']['numerator'],969);self.assertEqual(r['exact_value_percentage']['denominator'],146);self.assertGreater(r['ordinary_percentage_bounds'][0]['numerator'],0)
 def test_down_unsigned_is_negative(self):self.assertEqual(reported(cell('▼16.67','s'))[0],Fraction('-16.67'))
 def test_conflicting_arrow_not_silently_changed(self):self.assertTrue(reported(cell('▼+6.85','s'))[-1])
 def test_percent_format_not_applied_to_text(self):self.assertEqual(reported(cell('▲21.59','s','0.0%'))[0],Fraction('21.59'))
 def test_literal_text_not_rounded_by_numeric_format(self):self.assertEqual(amount(cell('1.096','s','#,##0'))[1],Fraction('1.096'))
 def test_numeric_display(self):self.assertEqual(amount(cell('155.69'))[1],156)
 def test_missing_not_zero(self):self.assertEqual(replay(dict(current_source=None,prior_source=cell('146'),percentage_source=cell('▼-100.00','s')))['status'],UNAVAILABLE)
 def test_zero_denominator(self):self.assertEqual(replay(dict(current_source=cell('5'),prior_source=cell('0'),percentage_source=cell('▲100','s')))['status'],UNAVAILABLE)
 def test_unsupported_format(self):
  with self.assertRaises(ValueError):amount(cell('2','n','General'))
 def test_horizontal_nonzero_rejected(self):
  with self.assertRaises(ValueError):reported(cell('►1.00','s'))
if __name__=='__main__':unittest.main()
